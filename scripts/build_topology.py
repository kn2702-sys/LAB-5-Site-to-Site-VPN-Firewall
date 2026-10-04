#!/usr/bin/env python3
"""Build Lab 5 .pkt topologies (working + two scenario variants).

Requires the pt_codec package from https://github.com/w4lven/claude-to-packet-tracer
(cloned to /tmp/ctt in the original build; adjust PT_CODEC_SRC below).

Usage:
    python3 scripts/build_topology.py

Output:
    Lab-5-Site-to-Site-VPN-Firewall.pkt                 (working: tunnel comes up on interesting traffic)
    Lab-5-SCENARIO-1-Tunnel-Up-No-Traffic.pkt           (fault: firewall policy drops decrypted traffic on FW-B)
    Lab-5-SCENARIO-2-Tunnel-Down.pkt                    (fault: IKE pre-shared-key mismatch on FW-B)
"""
from __future__ import annotations

import sys
from pathlib import Path

PT_CODEC_SRC = Path("/tmp/ctt/src")          # pip-free import of pt_codec
LIBRARY_DIR = Path("/tmp/ctt/samples/library")
SKELETON_PKT = Path("/tmp/ctt/samples/template.pkt")

sys.path.insert(0, str(PT_CODEC_SRC))

from pt_codec import Topology  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent

PSK = "C1sco12345"          # lab pre-shared key (use a strong random key in production)
FW_A_OUTSIDE = "203.0.113.1"
FW_B_OUTSIDE = "198.51.100.2"

# ---------------------------------------------------------------------------
# Device configs (also mirrored under configs/ as paste-ready text files)
# ---------------------------------------------------------------------------

FW_A_CONFIG = f"""!
! Lab 5 - FW-A : site-to-site IPsec VPN gateway + edge firewall (Office A)
! Inside : 10.10.10.0/24 | Outside : {FW_A_OUTSIDE}/30 | Peer : {FW_B_OUTSIDE}
!
hostname FW-A
!
no ip domain-lookup
!
interface GigabitEthernet0/0/0
 description *** INSIDE - Office A 10.10.10.0/24 ***
 ip address 10.10.10.1 255.255.255.0
 ip nat inside
 ip access-group 110 in
 no shutdown
!
interface GigabitEthernet0/0/1
 description *** OUTSIDE - Internet (to ISP) ***
 ip address {FW_A_OUTSIDE} 255.255.255.252
 ip nat outside
 crypto map VPN-MAP
 no shutdown
!
interface GigabitEthernet0/0/2
 description *** UNUSED ***
 shutdown
!
ip route 0.0.0.0 0.0.0.0 203.0.113.2
!
! --- NAT with exemption: VPN interesting traffic is never translated ---
access-list 101 deny ip 10.10.10.0 0.0.0.255 10.20.20.0 0.0.0.255
access-list 101 permit ip 10.10.10.0 0.0.0.255 any
ip nat inside source list 101 interface GigabitEthernet0/0/1 overload
!
! --- IKE Phase 1 ---
crypto isakmp policy 10
 encr aes
 hash sha
 authentication pre-share
 group 2
 lifetime 86400
crypto isakmp key {PSK} address {FW_B_OUTSIDE}
!
! --- IPsec Phase 2 ---
crypto ipsec transform-set ESP-AES-SHA esp-aes esp-sha-hmac
 mode tunnel
!
crypto map VPN-MAP 10 ipsec-isakmp
 description *** Site-to-site VPN to Office B ***
 set peer {FW_B_OUTSIDE}
 set transform-set ESP-AES-SHA
 set pfs group2
 match address 100
!
! --- Interesting traffic = the VPN selectors (proxy identities) ---
access-list 100 permit ip 10.10.10.0 0.0.0.255 10.20.20.0 0.0.0.255
!
! --- Firewall policy: edge ACL inbound on the inside interface ---
access-list 110 permit ip 10.10.10.0 0.0.0.255 10.20.20.0 0.0.0.255
access-list 110 permit tcp 10.10.10.0 0.0.0.255 any eq 80
access-list 110 permit tcp 10.10.10.0 0.0.0.255 any eq 443
access-list 110 permit udp 10.10.10.0 0.0.0.255 any eq 53
access-list 110 permit icmp 10.10.10.0 0.0.0.255 any
access-list 110 deny ip any any
!
end
"""

FW_B_CONFIG = f"""!
! Lab 5 - FW-B : site-to-site IPsec VPN gateway + edge firewall (Office B)
! Inside : 10.20.20.0/24 | Outside : {FW_B_OUTSIDE}/30 | Peer : {FW_A_OUTSIDE}
!
hostname FW-B
!
no ip domain-lookup
!
interface GigabitEthernet0/0/0
 description *** INSIDE - Office B 10.20.20.0/24 ***
 ip address 10.20.20.1 255.255.255.0
 ip nat inside
 ip access-group 110 in
 no shutdown
!
interface GigabitEthernet0/0/1
 description *** OUTSIDE - Internet (to ISP) ***
 ip address {FW_B_OUTSIDE} 255.255.255.252
 ip nat outside
 crypto map VPN-MAP
 no shutdown
!
interface GigabitEthernet0/0/2
 description *** UNUSED ***
 shutdown
!
ip route 0.0.0.0 0.0.0.0 198.51.100.1
!
! --- NAT with exemption: VPN interesting traffic is never translated ---
access-list 101 deny ip 10.20.20.0 0.0.0.255 10.10.10.0 0.0.0.255
access-list 101 permit ip 10.20.20.0 0.0.0.255 any
ip nat inside source list 101 interface GigabitEthernet0/0/1 overload
!
! --- IKE Phase 1 ---
crypto isakmp policy 10
 encr aes
 hash sha
 authentication pre-share
 group 2
 lifetime 86400
crypto isakmp key {PSK} address {FW_A_OUTSIDE}
!
! --- IPsec Phase 2 ---
crypto ipsec transform-set ESP-AES-SHA esp-aes esp-sha-hmac
 mode tunnel
!
crypto map VPN-MAP 10 ipsec-isakmp
 description *** Site-to-site VPN to Office A ***
 set peer {FW_A_OUTSIDE}
 set transform-set ESP-AES-SHA
 set pfs group2
 match address 100
!
! --- Interesting traffic = the VPN selectors (proxy identities) ---
access-list 100 permit ip 10.20.20.0 0.0.0.255 10.10.10.0 0.0.0.255
!
! --- Firewall policy: edge ACL inbound on the inside interface ---
access-list 110 permit ip 10.20.20.0 0.0.0.255 10.10.10.0 0.0.0.255
access-list 110 permit tcp 10.20.20.0 0.0.0.255 any eq 80
access-list 110 permit tcp 10.20.20.0 0.0.0.255 any eq 443
access-list 110 permit udp 10.20.20.0 0.0.0.255 any eq 53
access-list 110 permit icmp 10.20.20.0 0.0.0.255 any
access-list 110 deny ip any any
!
end
"""

ISP_CONFIG = """!
! Lab 5 - Simulated Internet (plain transit, no crypto, no NAT)
!
hostname ISP-Router
!
no ip domain-lookup
!
interface GigabitEthernet0/0/0
 description *** to FW-A 203.0.113.0/30 ***
 ip address 203.0.113.2 255.255.255.252
 no shutdown
!
interface GigabitEthernet0/0/1
 description *** to FW-B 198.51.100.0/30 ***
 ip address 198.51.100.1 255.255.255.252
 no shutdown
!
interface GigabitEthernet0/0/2
 description *** UNUSED ***
 shutdown
!
end
"""

SW_A_CONFIG = """!
! Lab 5 - Office A LAN switch (plain L2)
!
hostname SW-A
!
interface FastEthernet0/1
 description *** PC-A1 ***
 switchport mode access
 spanning-tree portfast
!
interface FastEthernet0/2
 description *** PC-A2 ***
 switchport mode access
 spanning-tree portfast
!
interface FastEthernet0/24
 description *** Uplink to FW-A ***
 switchport mode access
!
end
"""

SW_B_CONFIG = """!
! Lab 5 - Office B LAN switch (plain L2)
!
hostname SW-B
!
interface FastEthernet0/1
 description *** PC-B1 ***
 switchport mode access
 spanning-tree portfast
!
interface FastEthernet0/2
 description *** PC-B2 ***
 switchport mode access
 spanning-tree portfast
!
interface FastEthernet0/24
 description *** Uplink to FW-B ***
 switchport mode access
!
end
"""

# --- Scenario 1 fault: firewall policy on FW-B drops decrypted VPN traffic ---
# Applied OUTBOUND on FW-B's inside interface. The tunnel still establishes
# (ISAKMP + IPsec SAs come up), but data plane traffic A->B is denied after
# decryption. Evidence: `show crypto ipsec sa` counters move, `show
# access-lists 150` deny counter climbs.
SCENARIO1_FW_B_PATCH = [
    "access-list 150 deny ip 10.10.10.0 0.0.0.255 10.20.20.0 0.0.0.255",
    "access-list 150 permit ip any any",
]

# --- Scenario 2 fault: IKE pre-shared-key mismatch on FW-B ---
# Phase 1 can never complete, so no tunnel forms at all.
SCENARIO2_FW_B_PSK = "WrongKey999"


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(scenario: str = "working") -> Topology:
    t = Topology.open(SKELETON_PKT)
    t.clear()  # blank canvas, keeps PT version metadata

    # ---- devices (x, y = logical workspace coordinates) ----
    t.add_device_by_model(LIBRARY_DIR, "ISR4331", "FW-A", x=300, y=250)
    t.add_device_by_model(LIBRARY_DIR, "ISR4331", "ISP-Router", x=550, y=250)
    t.add_device_by_model(LIBRARY_DIR, "ISR4331", "FW-B", x=800, y=250)
    t.add_device_by_model(LIBRARY_DIR, "2960-24TT", "SW-A", x=300, y=420)
    t.add_device_by_model(LIBRARY_DIR, "2960-24TT", "SW-B", x=800, y=420)
    t.add_device_by_model(LIBRARY_DIR, "PC-PT", "PC-A1", x=200, y=580)
    t.add_device_by_model(LIBRARY_DIR, "PC-PT", "PC-A2", x=400, y=580)
    t.add_device_by_model(LIBRARY_DIR, "PC-PT", "PC-B1", x=700, y=580)
    t.add_device_by_model(LIBRARY_DIR, "PC-PT", "PC-B2", x=900, y=580)

    # ---- links ----
    # Office A LAN
    t.add_link("SW-A", "FastEthernet0/1", "PC-A1", "FastEthernet0")
    t.add_link("SW-A", "FastEthernet0/2", "PC-A2", "FastEthernet0")
    t.add_link("SW-A", "FastEthernet0/24", "FW-A", "GigabitEthernet0/0/0")
    # Internet transit (crossover, router to router)
    t.add_link("FW-A", "GigabitEthernet0/0/1",
               "ISP-Router", "GigabitEthernet0/0/0",
               cable_type="eCopperCrossOver")
    t.add_link("ISP-Router", "GigabitEthernet0/0/1",
               "FW-B", "GigabitEthernet0/0/1",
               cable_type="eCopperCrossOver")
    # Office B LAN
    t.add_link("FW-B", "GigabitEthernet0/0/0", "SW-B", "FastEthernet0/24")
    t.add_link("SW-B", "FastEthernet0/1", "PC-B1", "FastEthernet0")
    t.add_link("SW-B", "FastEthernet0/2", "PC-B2", "FastEthernet0")

    # ---- configs ----
    fw_b_config = FW_B_CONFIG
    if scenario == "scenario1":
        # inject the bad firewall policy into FW-B's running config
        lines = fw_b_config.splitlines()
        out = []
        for line in lines:
            out.append(line)
            if line.strip() == "ip access-group 110 in":
                out.append(" ip access-group 150 out")
        # append ACL 150 just before the final `end`
        idx = len(out) - 1 - out[::-1].index("end")
        out[idx:idx] = ["!"] + SCENARIO1_FW_B_PATCH + ["!"]
        fw_b_config = "\n".join(out) + "\n"
    elif scenario == "scenario2":
        fw_b_config = fw_b_config.replace(
            f"crypto isakmp key {PSK} address {FW_A_OUTSIDE}",
            f"crypto isakmp key {SCENARIO2_FW_B_PSK} address {FW_A_OUTSIDE}",
        )

    t.set_running_config("FW-A", FW_A_CONFIG)
    t.set_running_config("FW-B", fw_b_config)
    t.set_running_config("ISP-Router", ISP_CONFIG)
    t.set_running_config("SW-A", SW_A_CONFIG)
    t.set_running_config("SW-B", SW_B_CONFIG)

    # ---- end-device IP plans ----
    t.set_pc_network("PC-A1", ip="10.10.10.10", mask="255.255.255.0", gateway="10.10.10.1")
    t.set_pc_network("PC-A2", ip="10.10.10.11", mask="255.255.255.0", gateway="10.10.10.1")
    t.set_pc_network("PC-B1", ip="10.20.20.10", mask="255.255.255.0", gateway="10.20.20.1")
    t.set_pc_network("PC-B2", ip="10.20.20.11", mask="255.255.255.0", gateway="10.20.20.1")
    return t


def verify(t: Topology, scenario: str) -> None:
    names = {d.name for d in t.list_devices()}
    expected = {"FW-A", "FW-B", "ISP-Router", "SW-A", "SW-B",
                "PC-A1", "PC-A2", "PC-B1", "PC-B2"}
    assert expected <= names, f"missing devices: {expected - names}"
    assert len(t.list_links()) == 8, f"expected 8 links, got {len(t.list_links())}"

    fa = t.get_running_config("FW-A")
    for needle in ["crypto map VPN-MAP", "crypto isakmp policy 10",
                   f"crypto isakmp key {PSK} address {FW_B_OUTSIDE}",
                   "set peer 198.51.100.2", "match address 100",
                   "access-list 100 permit ip 10.10.10.0 0.0.0.255 10.20.20.0 0.0.0.255",
                   "access-list 101 deny ip 10.10.10.0 0.0.0.255 10.20.20.0 0.0.0.255",
                   "ip nat inside source list 101",
                   "ip access-group 110 in"]:
        assert needle in fa, f"FW-A config missing: {needle!r}"

    fb = t.get_running_config("FW-B")
    assert "set peer 203.0.113.1" in fb
    if scenario == "scenario1":
        assert "ip access-group 150 out" in fb, "scenario1: ACL 150 not applied"
        assert "access-list 150 deny ip 10.10.10.0 0.0.0.255 10.20.20.0 0.0.0.255" in fb
    elif scenario == "scenario2":
        assert f"crypto isakmp key {SCENARIO2_FW_B_PSK} address" in fb, "scenario2: PSK not broken"
        assert f"crypto isakmp key {PSK} address" not in fb
    else:
        assert f"crypto isakmp key {PSK} address {FW_A_OUTSIDE}" in fb

    assert t.get_pc_network("PC-A1")["gateway"] == "10.10.10.1"
    assert t.get_pc_network("PC-B1")["gateway"] == "10.20.20.1"
    print(f"  verify({scenario}): OK "
          f"({len(t.list_devices())} devices, {len(t.list_links())} links)")


def main() -> int:
    builds = [
        ("working", "Lab-5-Site-to-Site-VPN-Firewall.pkt"),
        ("scenario1", "Lab-5-SCENARIO-1-Tunnel-Up-No-Traffic.pkt"),
        ("scenario2", "Lab-5-SCENARIO-2-Tunnel-Down.pkt"),
    ]
    for scenario, fname in builds:
        print(f"building {fname} ...")
        t = build(scenario=scenario)
        verify(t, scenario)
        out = OUT_DIR / fname
        t.save(out)
        print(f"  saved {out} ({out.stat().st_size} bytes)")

    probe = Topology.open(OUT_DIR / "Lab-5-Site-to-Site-VPN-Firewall.pkt")
    assert len(probe.list_devices()) == 9 and len(probe.list_links()) == 8
    assert "crypto map VPN-MAP" in probe.get_running_config("FW-A")
    print("round-trip decode: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
