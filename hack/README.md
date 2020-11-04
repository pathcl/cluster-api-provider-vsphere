# Quickstart cluster-api vsphere


What you'll need

- k3s/kind or any existent kubernetes cluster
- Network access to vsphere api
- Dhcp running the destination network (VSPHERE_NETWORK)
- Vsphere templates. Check [here](https://github.com/kubernetes-sigs/cluster-api-provider-vsphere#kubernetes-versions-with-published-ovas)
-   For this case we'll use [ubuntu-1804-kube-v1.18.2](http://storage.googleapis.com/capv-images/release/v1.18.2/ubuntu-1804-kube-v1.18.2.ova). Don't forget to import them in your vsphere and mark them as template. 
- Coffee ☕


Quick intro [here](https://www.youtube.com/watch?v=gwCzfAdPCQg)

Assuming you don't have any running cluster we'll install k3s.

    $ curl -sfL https://get.k3s.io | sh -
    [sudo] password for pathcl: 
    [INFO]  Finding release for channel stable
    [INFO]  Using v1.18.9+k3s1 as release
    [INFO]  Downloading hash https://github.com/rancher/k3s/releases/download/v1.18.9+k3s1/sha256sum-amd64.txt
    [INFO]  Downloading binary https://github.com/rancher/k3s/releases/download/v1.18.9+k3s1/k3s
    [INFO]  Verifying binary download
    [INFO]  Installing k3s to /usr/local/bin/k3s
    [INFO]  Skipping /usr/local/bin/kubectl symlink to k3s, command exists in PATH at /home/pathcl/go/bin/kubectl
    [INFO]  Creating /usr/local/bin/crictl symlink to k3s
    [INFO]  Skipping /usr/local/bin/ctr symlink to k3s, command exists in PATH at /usr/bin/ctr
    [INFO]  Creating killall script /usr/local/bin/k3s-killall.sh
    [INFO]  Creating uninstall script /usr/local/bin/k3s-uninstall.sh
    [INFO]  env: Creating environment file /etc/systemd/system/k3s.service.env
    [INFO]  systemd: Creating service file /etc/systemd/system/k3s.service
    [INFO]  systemd: Enabling k3s unit
    Created symlink /etc/systemd/system/multi-user.target.wants/k3s.service → /etc/systemd/system/k3s.service.
    [INFO]  systemd: Starting k3s
    kind-control-plane   Ready    master   16h   v1.18.2

    $ sudo chown pathcl:pathcl /etc/rancher/k3s/k3s.yaml 
    $ export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
    $ kubectl get no
    NAME   STATUS   ROLES    AGE    VERSION
    puma   Ready    master   108s   v1.18.9+k3s1


At this point we have k3s up and running. Now we are ready to deploy cluster-api-provider. You'll need yo create a file named: $HOME/.cluster-api/clusterctl.yaml 

    $ cat /home/pathcl/.cluster-api/clusterctl.yaml 
    ## -- Controller settings -- ##
    VSPHERE_USERNAME: "administrator@vsphere.local"                    # The username used to access the remote vSphere endpoint
    VSPHERE_PASSWORD: "somepassword"                                  # The password used to access the remote vSphere endpoint

    ## -- Required workload cluster default settings -- ##
    VSPHERE_SERVER: "192.168.1.60"                                    # The vCenter server IP or FQDN
    VSPHERE_DATACENTER: "LabDC"                                # The vSphere datacenter to deploy the management cluster on
    VSPHERE_DATASTORE: "Esxi_LocalSSD"                         # The vSphere datastore to deploy the management cluster on
    VSPHERE_NETWORK: "VM Network"                                 # The VM network to deploy the management cluster on
    VSPHERE_RESOURCE_POOL: "*/Resources"                          # The vSphere resource pool for your VMs
    VSPHERE_FOLDER: ""                                          # The VM folder for your VMs. Set to "" to use the root vSphere folder
    VSPHERE_TEMPLATE: "ubuntu-1804-kube-v1.18.2"                  # The VM template to use for your management cluster.
    CONTROL_PLANE_ENDPOINT_IP: "192.168.1.230"                    # the IP that kube-vip is going to use as a control plane endpoint
    EXP_CLUSTER_RESOURCE_SET: "true"                              # This enables the ClusterResourceSet feature that we are using to deploy CSI
    VSPHERE_SSH_AUTHORIZED_KEY: "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCoJKZ7dZJVV3+U6zXRvvQSyFeM2QXgfK/CyboGsPvi/ApNk7HpGNg+ws1FTYlDeztgsecfsgkmNgsKv6X+zaBB3ljy7HGlqZs2JSzbVT1/CKQ7m3ZQssHykFYOBVrTHO9+PzBaYhgosU8DqT/joId3mk+G2QnaXr0e6oYd9P8df101c9EOCZyg9oZ2t3TEotPQE2gMwInnDX1NXF/w+xDWOzRU7E+1cwZusuPtXPgXQdlheHOQ4pi+obx/f3Ur8DRURNe68cof1d+ByaYCDWQCONqyzCCRXzkpOX1ZULL2PSj5quXkpaA/ZRdxTQuonXvKTCcUsAC1BYwvMeYtrlQN pathcl@kepler" 


Download clusterctl binary.

    $ sudo curl -Lo /usr/bin/clusterctl https://github.com/kubernetes-sigs/cluster-api/releases/download/v0.3.10/clusterctl-linux-amd64
      % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                     Dload  Upload   Total   Spent    Left  Speed
    100   648  100   648    0     0   2257      0 --:--:-- --:--:-- --:--:--  2250
    100 48.7M  100 48.7M    0     0  2572k      0  0:00:19  0:00:19 --:--:-- 1978k

    $ sudo chmod a+x /usr/bin/clusterctl

Now we deploy cluster-api-vsphere in our management cluster (k3s)


    $ /usr/bin/clusterctl init --infrastructure vsphere -v5
    Using configuration File="/home/pathcl/.cluster-api/clusterctl.yaml"
    Installing the clusterctl inventory CRD
    Creating CustomResourceDefinition="providers.clusterctl.cluster.x-k8s.io"
    Fetching providers
    Fetching File="core-components.yaml" Provider="cluster-api" Version="v0.3.10"
    Fetching File="bootstrap-components.yaml" Provider="bootstrap-kubeadm" Version="v0.3.10"
    Fetching File="control-plane-components.yaml" Provider="control-plane-kubeadm" Version="v0.3.10"
    Fetching File="infrastructure-components.yaml" Provider="infrastructure-vsphere" Version="v0.7.1"
    Fetching File="metadata.yaml" Provider="cluster-api" Version="v0.3.10"
    Fetching File="metadata.yaml" Provider="bootstrap-kubeadm" Version="v0.3.10"
    Fetching File="metadata.yaml" Provider="control-plane-kubeadm" Version="v0.3.10"
    Fetching File="metadata.yaml" Provider="infrastructure-vsphere" Version="v0.7.1"
    Creating Namespace="cert-manager-test"
    Installing cert-manager Version="v0.16.1"
    Creating Namespace="cert-manager"
    Creating CustomResourceDefinition="certificaterequests.cert-manager.io"
    Creating CustomResourceDefinition="certificates.cert-manager.io"
    Creating CustomResourceDefinition="challenges.acme.cert-manager.io"
    Creating CustomResourceDefinition="clusterissuers.cert-manager.io"
    Creating CustomResourceDefinition="issuers.cert-manager.io"
    Creating CustomResourceDefinition="orders.acme.cert-manager.io"
    Creating ServiceAccount="cert-manager-cainjector" Namespace="cert-manager"
    Creating ServiceAccount="cert-manager" Namespace="cert-manager"
    Creating ServiceAccount="cert-manager-webhook" Namespace="cert-manager"
    Creating ClusterRole="cert-manager-cainjector"
    Creating ClusterRole="cert-manager-controller-issuers"
    Creating ClusterRole="cert-manager-controller-clusterissuers"
    Creating ClusterRole="cert-manager-controller-certificates"
    Creating ClusterRole="cert-manager-controller-orders"
    Creating ClusterRole="cert-manager-controller-challenges"
    Creating ClusterRole="cert-manager-controller-ingress-shim"
    Creating ClusterRole="cert-manager-view"
    Creating ClusterRole="cert-manager-edit"
    Creating ClusterRoleBinding="cert-manager-cainjector"
    Creating ClusterRoleBinding="cert-manager-controller-issuers"
    Creating ClusterRoleBinding="cert-manager-controller-clusterissuers"
    Creating ClusterRoleBinding="cert-manager-controller-certificates"
    Creating ClusterRoleBinding="cert-manager-controller-orders"
    Creating ClusterRoleBinding="cert-manager-controller-challenges"
    Creating ClusterRoleBinding="cert-manager-controller-ingress-shim"
    Creating Role="cert-manager-cainjector:leaderelection" Namespace="kube-system"
    Creating Role="cert-manager:leaderelection" Namespace="kube-system"
    Creating Role="cert-manager-webhook:dynamic-serving" Namespace="cert-manager"
    Creating RoleBinding="cert-manager-cainjector:leaderelection" Namespace="kube-system"
    Creating RoleBinding="cert-manager:leaderelection" Namespace="kube-system"
    Creating RoleBinding="cert-manager-webhook:dynamic-serving" Namespace="cert-manager"
    Creating Service="cert-manager" Namespace="cert-manager"
    Creating Service="cert-manager-webhook" Namespace="cert-manager"
    Creating Deployment="cert-manager-cainjector" Namespace="cert-manager"
    Creating Deployment="cert-manager" Namespace="cert-manager"
    Creating Deployment="cert-manager-webhook" Namespace="cert-manager"
    Creating MutatingWebhookConfiguration="cert-manager-webhook"
    Creating ValidatingWebhookConfiguration="cert-manager-webhook"
    Waiting for cert-manager to be available...
    Updating Namespace="cert-manager-test"
    Creating Issuer="test-selfsigned" Namespace="cert-manager-test"
    Creating Issuer="test-selfsigned" Namespace="cert-manager-test"
    Creating Issuer="test-selfsigned" Namespace="cert-manager-test"
    Creating Issuer="test-selfsigned" Namespace="cert-manager-test"
    Creating Issuer="test-selfsigned" Namespace="cert-manager-test"
    Creating Issuer="test-selfsigned" Namespace="cert-manager-test"
    Creating Issuer="test-selfsigned" Namespace="cert-manager-test"
    Creating Issuer="test-selfsigned" Namespace="cert-manager-test"
    Creating Certificate="selfsigned-cert" Namespace="cert-manager-test"
    Deleting Namespace="cert-manager-test"
    Deleting Issuer="test-selfsigned" Namespace="cert-manager-test"
    Deleting Certificate="selfsigned-cert" Namespace="cert-manager-test"
    Installing Provider="cluster-api" Version="v0.3.10" TargetNamespace="capi-system"
    Creating shared objects Provider="cluster-api" Version="v0.3.10"
    Creating Namespace="capi-webhook-system"
    Creating CustomResourceDefinition="clusterresourcesetbindings.addons.cluster.x-k8s.io"
    Creating CustomResourceDefinition="clusterresourcesets.addons.cluster.x-k8s.io"
    Creating CustomResourceDefinition="clusters.cluster.x-k8s.io"
    Creating CustomResourceDefinition="machinedeployments.cluster.x-k8s.io"
    Creating CustomResourceDefinition="machinehealthchecks.cluster.x-k8s.io"
    Creating CustomResourceDefinition="machinepools.exp.cluster.x-k8s.io"
    Creating CustomResourceDefinition="machines.cluster.x-k8s.io"
    Creating CustomResourceDefinition="machinesets.cluster.x-k8s.io"
    Creating MutatingWebhookConfiguration="capi-mutating-webhook-configuration"
    Creating Service="capi-webhook-service" Namespace="capi-webhook-system"
    Creating Deployment="capi-controller-manager" Namespace="capi-webhook-system"
    Creating Certificate="capi-serving-cert" Namespace="capi-webhook-system"
    Creating Issuer="capi-selfsigned-issuer" Namespace="capi-webhook-system"
    Creating ValidatingWebhookConfiguration="capi-validating-webhook-configuration"
    Creating instance objects Provider="cluster-api" Version="v0.3.10" TargetNamespace="capi-system"
    Creating Namespace="capi-system"
    Creating Role="capi-leader-election-role" Namespace="capi-system"
    Creating ClusterRole="capi-system-capi-aggregated-manager-role"
    Creating ClusterRole="capi-system-capi-manager-role"
    Creating ClusterRole="capi-system-capi-proxy-role"
    Creating RoleBinding="capi-leader-election-rolebinding" Namespace="capi-system"
    Creating ClusterRoleBinding="capi-system-capi-manager-rolebinding"
    Creating ClusterRoleBinding="capi-system-capi-proxy-rolebinding"
    Creating Service="capi-controller-manager-metrics-service" Namespace="capi-system"
    Creating Deployment="capi-controller-manager" Namespace="capi-system"
    Creating inventory entry Provider="cluster-api" Version="v0.3.10" TargetNamespace="capi-system"
    Installing Provider="bootstrap-kubeadm" Version="v0.3.10" TargetNamespace="capi-kubeadm-bootstrap-system"
    Creating shared objects Provider="bootstrap-kubeadm" Version="v0.3.10"
    Creating CustomResourceDefinition="kubeadmconfigs.bootstrap.cluster.x-k8s.io"
    Creating CustomResourceDefinition="kubeadmconfigtemplates.bootstrap.cluster.x-k8s.io"
    Creating Service="capi-kubeadm-bootstrap-webhook-service" Namespace="capi-webhook-system"
    Creating Deployment="capi-kubeadm-bootstrap-controller-manager" Namespace="capi-webhook-system"
    Creating Certificate="capi-kubeadm-bootstrap-serving-cert" Namespace="capi-webhook-system"
    Creating Issuer="capi-kubeadm-bootstrap-selfsigned-issuer" Namespace="capi-webhook-system"
    Creating ValidatingWebhookConfiguration="capi-kubeadm-bootstrap-validating-webhook-configuration"
    Creating instance objects Provider="bootstrap-kubeadm" Version="v0.3.10" TargetNamespace="capi-kubeadm-bootstrap-system"
    Creating Namespace="capi-kubeadm-bootstrap-system"
    Creating Role="capi-kubeadm-bootstrap-leader-election-role" Namespace="capi-kubeadm-bootstrap-system"
    Creating ClusterRole="capi-kubeadm-bootstrap-system-capi-kubeadm-bootstrap-manager-role"
    Creating ClusterRole="capi-kubeadm-bootstrap-system-capi-kubeadm-bootstrap-proxy-role"
    Creating RoleBinding="capi-kubeadm-bootstrap-leader-election-rolebinding" Namespace="capi-kubeadm-bootstrap-system"
    Creating ClusterRoleBinding="capi-kubeadm-bootstrap-system-capi-kubeadm-bootstrap-manager-rolebinding"
    Creating ClusterRoleBinding="capi-kubeadm-bootstrap-system-capi-kubeadm-bootstrap-proxy-rolebinding"
    Creating Service="capi-kubeadm-bootstrap-controller-manager-metrics-service" Namespace="capi-kubeadm-bootstrap-system"
    Creating Deployment="capi-kubeadm-bootstrap-controller-manager" Namespace="capi-kubeadm-bootstrap-system"
    Creating inventory entry Provider="bootstrap-kubeadm" Version="v0.3.10" TargetNamespace="capi-kubeadm-bootstrap-system"
    Installing Provider="control-plane-kubeadm" Version="v0.3.10" TargetNamespace="capi-kubeadm-control-plane-system"
    Creating shared objects Provider="control-plane-kubeadm" Version="v0.3.10"
    Creating CustomResourceDefinition="kubeadmcontrolplanes.controlplane.cluster.x-k8s.io"
    Creating MutatingWebhookConfiguration="capi-kubeadm-control-plane-mutating-webhook-configuration"
    Creating Service="capi-kubeadm-control-plane-webhook-service" Namespace="capi-webhook-system"
    Creating Deployment="capi-kubeadm-control-plane-controller-manager" Namespace="capi-webhook-system"
    Creating Certificate="capi-kubeadm-control-plane-serving-cert" Namespace="capi-webhook-system"
    Creating Issuer="capi-kubeadm-control-plane-selfsigned-issuer" Namespace="capi-webhook-system"
    Creating ValidatingWebhookConfiguration="capi-kubeadm-control-plane-validating-webhook-configuration"
    Creating instance objects Provider="control-plane-kubeadm" Version="v0.3.10" TargetNamespace="capi-kubeadm-control-plane-system"
    Creating Namespace="capi-kubeadm-control-plane-system"
    Creating Role="capi-kubeadm-control-plane-leader-election-role" Namespace="capi-kubeadm-control-plane-system"
    Creating ClusterRole="capi-kubeadm-control-plane-system-capi-kubeadm-control-plane-aggregated-manager-role"
    Creating ClusterRole="capi-kubeadm-control-plane-system-capi-kubeadm-control-plane-manager-role"
    Creating ClusterRole="capi-kubeadm-control-plane-system-capi-kubeadm-control-plane-proxy-role"
    Creating RoleBinding="capi-kubeadm-control-plane-leader-election-rolebinding" Namespace="capi-kubeadm-control-plane-system"
    Creating ClusterRoleBinding="capi-kubeadm-control-plane-system-capi-kubeadm-control-plane-manager-rolebinding"
    Creating ClusterRoleBinding="capi-kubeadm-control-plane-system-capi-kubeadm-control-plane-proxy-rolebinding"
    Creating Service="capi-kubeadm-control-plane-controller-manager-metrics-service" Namespace="capi-kubeadm-control-plane-system"
    Creating Deployment="capi-kubeadm-control-plane-controller-manager" Namespace="capi-kubeadm-control-plane-system"
    Creating inventory entry Provider="control-plane-kubeadm" Version="v0.3.10" TargetNamespace="capi-kubeadm-control-plane-system"
    Installing Provider="infrastructure-vsphere" Version="v0.7.1" TargetNamespace="capv-system"
    Creating shared objects Provider="infrastructure-vsphere" Version="v0.7.1"
    Creating CustomResourceDefinition="haproxyloadbalancers.infrastructure.cluster.x-k8s.io"
    Creating CustomResourceDefinition="vsphereclusters.infrastructure.cluster.x-k8s.io"
    Creating CustomResourceDefinition="vspheremachines.infrastructure.cluster.x-k8s.io"
    Creating CustomResourceDefinition="vspheremachinetemplates.infrastructure.cluster.x-k8s.io"
    Creating CustomResourceDefinition="vspherevms.infrastructure.cluster.x-k8s.io"
    Creating Service="capv-webhook-service" Namespace="capi-webhook-system"
    Creating Deployment="capv-controller-manager" Namespace="capi-webhook-system"
    Creating Certificate="capv-serving-cert" Namespace="capi-webhook-system"
    Creating Issuer="capv-selfsigned-issuer" Namespace="capi-webhook-system"
    Creating ValidatingWebhookConfiguration="capv-validating-webhook-configuration"
    Creating instance objects Provider="infrastructure-vsphere" Version="v0.7.1" TargetNamespace="capv-system"
    Creating Namespace="capv-system"
    Creating Role="capv-leader-election-role" Namespace="capv-system"
    Creating ClusterRole="capv-system-capv-manager-role"
    Creating ClusterRole="capv-system-capv-proxy-role"
    Creating RoleBinding="capv-leader-election-rolebinding" Namespace="capv-system"
    Creating ClusterRoleBinding="capv-system-capv-manager-rolebinding"
    Creating ClusterRoleBinding="capv-system-capv-proxy-rolebinding"
    Creating Secret="capv-manager-bootstrap-credentials" Namespace="capv-system"
    Creating Service="capv-controller-manager-metrics-service" Namespace="capv-system"
    Creating Deployment="capv-controller-manager" Namespace="capv-system"
    Creating inventory entry Provider="infrastructure-vsphere" Version="v0.7.1" TargetNamespace="capv-system"

    Your management cluster has been initialized successfully!

    You can now create your first workload cluster by running the following:

      clusterctl config cluster [name] --kubernetes-version [version] | kubectl apply -f -

    Using configuration File="/home/pathcl/.cluster-api/clusterctl.yaml"

We need to wait until everything is running.

    $ kubectl get pods -A 
    NAMESPACE                           NAME                                                             READY   STATUS              RESTARTS   AGE
    kube-system                         metrics-server-7566d596c8-j7mrx                                  1/1     Running             0          5m50s
    kube-system                         local-path-provisioner-6d59f47c7-jhjl2                           1/1     Running             0          5m50s
    kube-system                         helm-install-traefik-h5kjr                                       0/1     Completed           0          5m51s
    kube-system                         svclb-traefik-qz9gr                                              2/2     Running             0          5m29s
    kube-system                         coredns-7944c66d8d-4tqqp                                         1/1     Running             0          5m50s
    kube-system                         traefik-758cd5fc85-5pq6x                                         1/1     Running             0          5m29s
    cert-manager                        cert-manager-cainjector-5ffff9dd7c-zxdxd                         1/1     Running             0          27s
    cert-manager                        cert-manager-578cd6d964-hg96p                                    1/1     Running             0          27s
    cert-manager                        cert-manager-webhook-556b9d7dfd-h9l85                            1/1     Running             0          27s
    capi-webhook-system                 capi-controller-manager-8d87dd984-kbcwd                          0/2     ContainerCreating   0          12s
    capi-system                         capi-controller-manager-58f88bff65-cjmz6                         0/2     ContainerCreating   0          12s
    capi-webhook-system                 capi-kubeadm-bootstrap-controller-manager-8496dcdbdb-h649w       0/2     ContainerCreating   0          12s
    capi-kubeadm-bootstrap-system       capi-kubeadm-bootstrap-controller-manager-86f4bcdf9f-8f6xg       0/2     ContainerCreating   0          12s
    capi-webhook-system                 capi-kubeadm-control-plane-controller-manager-77f644cd55-vm9mt   0/2     ContainerCreating   0          11s
    capi-kubeadm-control-plane-system   capi-kubeadm-control-plane-controller-manager-756df75c96-rfbtf   0/2     ContainerCreating   0          11s
    capi-webhook-system                 capv-controller-manager-64b45c8fdd-d2qd2                         0/2     ContainerCreating   0          10s
    capv-system                         capv-controller-manager-846f5b744f-bjvtr                         0/2     ContainerCreating   0          10s

Now we can start!


## Create cluster

Assuming you're in the same machine where k3s is running and you have cluster-admin access

    pyctl.py create -n lab01 -dc LabDC -u administrator@vsphere.local -s 192.168.1.60 -vip 192.168.1.240 -vlan 'VM Network' -t ubuntu-1804-kube-v1.18.2 -ds 'Esxi_LocalSSD'
    
Details:

    -n name of your cluster
    -dc name of your vcenter datacenter
    -u vcenter username
    -s vcenter ip
    -vip control plane endpoint (kube-vip)
    -vlan vlan where your cluster will run
    -t template to use
    -ds name of your vcenter datastore
    
## Upgrade cluster

Pre-requisites:

- You'll need a ova created by [image-builder](https://github.com/pathcl/image-builder)
- Packer [packer](https://packer.io)
- vsphere config for [packer](https://github.com/kubernetes-sigs/image-builder/blob/master/images/capi/packer/ova/vsphere.json)

Steps to create your own template. 

        git clone https://github.com/pathcl/image-builder
        cd image-builder/images/capi
        vi packer/ova/vsphere.json
        vi packer/config/kubernetes.json
        make build-node-ova-vsphere-ubuntu-1804 
   
Only then you can upgrade:

    pyctl.py upgrade -n lab01 -t ubuntu-1804-kube-v1.19.3 -U v1.19.3 -ds 'Esxi_LocalSSD' -dc LabDC
    
    
## Get kubeconfig

    pyctl.py kubeconfig -n lab01 

