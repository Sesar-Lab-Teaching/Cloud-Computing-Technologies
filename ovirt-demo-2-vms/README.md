# Virtualization with OVirt - 2 VMs

This implementation of the reference scenario is designed to be deployed on 2 virtual machines, created with  OVirt.

Starting from the [previous demo setup](../ovirt-demo-single-vm/), with a single VM `A`, we create an additional VM `B` that only hosts the web server. This instance of the web server communicates with the MySQL instance deployed on the VM `A`. 

To deploy the web server on the VM `B`, we need:

- [`main.py`](../ovirt-demo-single-vm/main.py)
- [`requirements.txt`](../ovirt-demo-single-vm/requirements.txt)
- `start.sh` (located in the current folder)
- A `.env` file with the following configurations:
    ```
    MYSQL_HOST=172.20.28.119    # the IP of VM A
    MYSQL_ROOT_PASSWORD=root
    MYSQL_USER=cct1
    MYSQL_PASSWORD=cct1-secret
    MYSQL_DATABASE=cct1
    MYSQL_PORT=3312             # the port exposed by VM A
    ```

Then run `./start.sh`.

Now there is a new deployment of the Web server on VM `B`, while the MySQL instance is running on a different VM, i.e. VM `A`.