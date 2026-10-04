# VPN Concepts: what this lab teaches (and how it maps to the real world)

## The honest frame

This lab runs on Cisco ISR routers in Packet Tracer — not a Palo Alto or
Fortinet appliance. That is deliberate, and it is also exactly what makes
the knowledge transferable: **site-to-site IPsec is a standard, not a
vendor.** IKE Phase 1, Phase 2, proxy identities, NAT exemption and policy
enforcement work the same way everywhere; only the knobs change names.

> You can truthfully say: *"Built and troubleshot a site-to-site VPN lab
> covering routing, tunnel establishment and firewall policy behavior."*
>
> Don't claim: *"I deployed enterprise IPsec VPN."*

If an interviewer asks "but have you used Palo Alto?", the credible answer
is: "I've built and broken IPsec tunnels hands-on — IKEv1 Phase 1/2,
selectors, NAT exemption, policy ordering. The Palo Alto concepts map
directly; I'd be learning its GUI, not the VPN fundamentals."

## Concept map: Cisco ↔ Palo Alto ↔ Fortinet

| Concept (what it does) | This lab (Cisco IOS) | Palo Alto PAN-OS | Fortinet FortiOS |
|---|---|---|---|
| Defines *what* gets encrypted | `access-list 100` + `match address 100` ("interesting traffic") | Proxy IDs / IPsec selectors | Phase 2 selectors |
| Phase 1 negotiation | `crypto isakmp policy 10` | IKE Gateway → IKE Crypto Profile | IKE Phase 1 proposal |
| Shared secret auth | `crypto isakmp key … address …` (PSK) | Pre-Shared Key on the IKE Gateway | Pre-shared key |
| Phase 2 encryption | `crypto ipsec transform-set` | IPsec Crypto Profile | Phase 2 proposal |
| Binds tunnel to an interface | `crypto map VPN-MAP` on the outside interface | Tunnel interface + IKE Gateway binding | VPN tunnel interface |
| Keeps VPN traffic un-NATed | ACL 101 deny-first NAT exemption | NAT exclusion / no-NAT rule above the source NAT | Firewall policy with NAT disabled |
| Firewall policy | Extended ACLs (`ip access-group … in/out`) | Security Policy (zones, apps) | Firewall Policy (interfaces, services) |

Learn the left column deeply and the other two become vocabulary.

## How a tunnel comes up (the 60-second version)

1. **Interesting traffic** — PC-A1 pings 10.20.20.10. FW-A checks ACL 100:
   source `10.10.10.0/24` → destination `10.20.20.0/24` matches. *This*
   traffic — and only this — is allowed into the tunnel.
2. **IKE Phase 1** — FW-A and FW-B negotiate `crypto isakmp policy 10`
   (AES, SHA, pre-shared auth, DH group 2) and authenticate with the PSK.
   Result: a secure management channel. Verify: `show crypto isakmp sa`
   → `QM_IDLE`.
3. **IPsec Phase 2** — they negotiate the transform set
   (`ESP-AES-SHA`, tunnel mode, PFS group 2) and agree on the selectors
   from ACL 100. Result: the data-plane SAs. Verify:
   `show crypto ipsec sa` → encaps/decaps counters moving.
4. **NAT exemption** — before encryption, FW-A consults ACL 101: VPN
   traffic hits the `deny` line first and skips NAT entirely. Without this,
   the source address would be PATed and the selectors would never match —
   the #1 silent killer of site-to-site VPNs.
5. **Firewall policy** — ACL 110 (inbound on inside) permits the VPN
   traffic alongside normal egress (web/DNS/ICMP) and denies the rest.

## The two failure modes in this repo (and in production)

- **Scenario 1 — tunnel up, no traffic.** Phase 1/2 completed, SAs exist,
  counters move on one side — but the application fails. Think *data
  plane*: routes, selectors, NAT exemption, firewall policy. See
  [SCENARIO-1.md](SCENARIO-1.md).
- **Scenario 2 — tunnel never forms.** No SAs at all. Think *control
  plane*: peer reachability, PSK, Phase 1/2 parameter mismatch. See
  [SCENARIO-2.md](SCENARIO-2.md).

Knowing which of these you're looking at — before touching any config —
is the skill. `show crypto isakmp sa` answers it in one line.

## Production notes (what I'd do differently with real appliances)

- IKEv2 instead of IKEv1; AES-256-GCM, SHA-256, DH group 14+ (this lab
  uses AES/SHA/DH2 because that's what Packet Tracer supports).
- PSKs generated per-tunnel and vaulted — never reused, never in chat.
- DPD (dead peer detection), tunnel monitoring / SLA failover.
- Logging the tunnel state to the SIEM; alerting on SA flaps.
