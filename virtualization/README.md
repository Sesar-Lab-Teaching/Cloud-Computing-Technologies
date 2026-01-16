# Virtualization

The hypervisor we use in this demo is KVM, the native hypervisor for Linux-based systems.

## VM Image

To guest OS we have chosen is Ubuntu, but [many versions are available](https://ubuntu.com/download). Two of them are more common than others:

- Ubuntu server (downloadable as `.iso`) - contains the installer, package sets and the necessary files to interactively install the OS in a disk partition. The installation can be automated with `autoinstall`.
- Ubuntu Cloud image (downloadable as `.img`) - A pre-installed Ubuntu file system ready to be used. It is intended to be deployed as a disk image for VMs or cloud instances and is configurable through `cloud-init`.

We are going to use the [Ubuntu 24.04 cloud image ](https://cloud-images.ubuntu.com).

---

## VM Configuration

We can configure the VMs using [`cloud-init`](https://cloudinit.readthedocs.io/en/latest/howto/launch_libvirt.html). The environment where the VM is started determines the datasource:

> Datasources are sources of configuration data for cloud-init that typically come from the user (i.e., user-data) or come from the cloud that created the configuration drive (i.e., meta-data). Typical user-data includes files, YAML, and shell scripts whereas typical meta-data includes server name, instance id, display name, and other cloud specific details.

In this scenario, there is no Cloud involved, so the datasource we are going to use is [`NoCloud`](https://cloudinit.readthedocs.io/en/latest/reference/datasources/nocloud.html).

The `user-data`, `meta-data`, and `network-config` files for each VM are in `cloud-init/` folder.

---

## DB - VM Creation

To create the VM for the DB, we first need to set a static IP address (`192.168.122.3`), ensuring the database can always be queried at the same IP.

```bash
sudo virsh net-update default add ip-dhcp-host \
    "<host mac='12:34:00:6b:3c:59' ip='192.168.122.3'/>" \
    --live --config
```

**Note**: the mac address must be set in the `network-config`.
Then, the VM can be created:

```bash
# Copy image to /var/lib/libvirt/images/
IMAGE_PATH="/var/lib/libvirt/images/noble-server-cloudimg-amd64.img"

virt-install --name db \
    --memory 4096 \
    --noreboot \
    --os-variant detect=on,name=ubuntunoble \
    --disk=size=25,backing_store="$IMAGE_PATH" \
    --cloud-init user-data="$(pwd)/cloud-init/db/user-data,meta-data=$(pwd)/cloud-init/db/meta-data,network-config=$(pwd)/cloud-init/db/network-config"
```

Run `virt-manager` to view and login into the VM. User: `ubuntu`, password: `cct-db` (see `user-data`). You can also login into it using the shell by running

```bash
virsh console db
```

---

## Webserver - VM Creation

The procedure to create the Webserver VM is even easier because we do not need to assign a static IP address and the network configs are the default ones. 

```bash
# Copy image to /var/lib/libvirt/images/
IMAGE_PATH="/var/lib/libvirt/images/noble-server-cloudimg-amd64.img"

virt-install --name web-server \
    --memory 4096 \
    --noreboot \
    --os-variant detect=on,name=ubuntunoble \
    --disk=size=25,backing_store="$IMAGE_PATH" \
    --cloud-init user-data="$(pwd)/cloud-init/webserver/user-data,meta-data=$(pwd)/cloud-init/webserver/meta-data"
```