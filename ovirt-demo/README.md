# IaaS with OVirt

This implementation of the reference scenario is designed to be deployed on a virtual machine, which can be easily created with  OVirt.

Once the VM is ready, copy this folder's files into the working directory of the VM and run:

```
docker-compose up -d
```

to start the web server and the MySQL instance.

If the VM and your host machine share the same network, you should be able to access the Web server from `http://{your-vm-ip}:5000`

---

From the VM:

- You can verify the MySQL instance is running by opening a shell and execute:

    ```
    mysql -u cct1 --password=cct1-secret -D cct1 --port 3312 --host 127.0.0.1 -e 'select * from accounts;'
    ```

- You can verify the web server is running by opening a shell and execute:

    ```
    curl http://localhost:5000
    ```