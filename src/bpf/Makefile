all:
	$(MAKE) -C bpf_lldp_egress/ all
	$(MAKE) -C xdp_lldp_ingress/ all
	$(MAKE) -C xdp_lldp_ingress_redirect/ all
	$(MAKE) -C xdp_pass/ all
	$(MAKE) -C xdp_redirect/ all

clean:
	$(MAKE) -C bpf_lldp_egress/ clean
	$(MAKE) -C xdp_lldp_ingress/ clean
	$(MAKE) -C xdp_lldp_ingress_redirect/ clean
	$(MAKE) -C xdp_pass/ clean
	$(MAKE) -C xdp_redirect/ clean
