#!/usr/bin/env python3
# TODO
# - remove harcoded items
# - write it in Go
# - mocks/pytest
# - addons cleanup

from base64 import b64decode
from kubernetes.utils import create_from_yaml
from collections import namedtuple
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from urllib3 import exceptions as urllib3_exceptions
from tempfile import mkstemp
from pprint import pprint

import getpass
import os
import requests
import kubernetes.client
import argparse
import time
import base64
import re
import string
import sys
import itertools
import warnings
import json


def create_crd(kind):
    config.load_kube_config()
    api = client.CustomObjectsApi()

    api.create_namespaced_custom_object(
        namespace="default",
        group=kind.group,
        version="v1alpha3",
        plural=str.lower(kind.plural),
        body=kind.body,
    )

def patch_crd(kind):
    config.load_kube_config()
    api = client.CustomObjectsApi()

    api.patch_namespaced_custom_object(
        namespace="default",
        name=kind.name,
        group=kind.group,
        version="v1alpha3",
        plural=str.lower(kind.plural),
        body=kind.body,
    )


def info_crd(kind):
    config.load_kube_config()
    api = client.CustomObjectsApi()
    api_response = api.get_namespaced_custom_object(
        namespace="default",
        group=kind.group,
        version="v1alpha3",
        plural=str.lower(kind.plural),
        name=kind.name)
    info = api_response['metadata']['resourceVersion'], api_response['metadata']['uid']
    return info

def replace_crd(kind):
    config.load_kube_config()
    api = client.CustomObjectsApi()
    api.replace_namespaced_custom_object(
        namespace="default",
        group=kind.group,
        version="v1alpha3",
        plural=str.lower(kind.plural),
        body=kind.body,
        name=kind.name
    )

def delete_crd(kind):
    config.load_kube_config()
    api = client.CustomObjectsApi()
    api.delete_namespaced_custom_object(
        namespace="default",
        name=kind.name,
        group=kind.group,
        version="v1alpha3",
        plural=str.lower(kind.plural),
        body=kubernetes.client.V1DeleteOptions()
    )



def delete_cluster(args):
    clustername = args.name + '-md-0'

    cluster = {
        "apiVersion": "cluster.x-k8s.io/v1alpha3",
        "kind": "Cluster",
        "metadata": {
            "name": args.name,
            "namespace": "default"
        },
        "spec": {
            "clusterNetwork": {
                "pods": {
                    "cidrBlocks": [
                        "172.16.0.0/16"
                    ]
                }
            },
            "controlPlaneRef": {
                "apiVersion": "controlplane.cluster.x-k8s.io/v1alpha3",
                "kind": "KubeadmControlPlane",
                "name": args.name
            },
            "infrastructureRef": {
                "apiVersion": "infrastructure.cluster.x-k8s.io/v1alpha3",
                "kind": "VSphereCluster",
                "name": args.name
            }
        }
    }


    kubeadmconfigtemplate = {
        "apiVersion": "bootstrap.cluster.x-k8s.io/v1alpha3",
        "kind": "KubeadmConfigTemplate",
        "metadata": {
            "name": clustername,
            "namespace": "default"
        },
        "spec": {
            "template": {
                "spec": {
                    "joinConfiguration": {
                        "nodeRegistration": {
                            "criSocket": "/var/run/containerd/containerd.sock",
                            "kubeletExtraArgs": {
                                "cloud-provider": "external"
                            },
                            "name": "{{ ds.meta_data.hostname }}"
                        }
                    },
                    "preKubeadmCommands": [
                        "hostname \"{{ ds.meta_data.hostname }}\"",
                        "echo \"::1         ipv6-localhost ipv6-loopback\" >/etc/hosts",
                        "echo \"127.0.0.1   localhost\" >>/etc/hosts",
                        "echo \"127.0.0.1   {{ ds.meta_data.hostname }}\" >>/etc/hosts",
                        "echo \"{{ ds.meta_data.hostname }}\" >/etc/hostname"
                    ],
                    "users": [
                        {
                            "name": "sysop",
                            "sshAuthorizedKeys": [
                                "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCoJKZ7dZJVV3+U6zXRvvQSyFeM2QXgfK/CyboGsPvi/ApNk7HpGNg+ws1FTYlDeztgsecfsgkmNgsKv6X+zaBB3ljy7HGlqZs2JSzbVT1/CKQ7m3ZQssHykFYOBVrTHO9+PzBaYhgosU8DqT/joId3mk+G2QnaXr0e6oYd9P8df101c9EOCZyg9oZ2t3TEotPQE2gMwInnDX1NXF/w+xDWOzRU7E+1cwZusuPtXPgXQdlheHOQ4pi+obx/f3Ur8DRURNe68cof1d+ByaYCDWQCONqyzCCRXzkpOX1ZULL2PSj5quXkpaA/ZRdxTQuonXvKTCcUsAC1BYwvMeYtrlQN pathcl@kepler"
                            ],
                            "sudo": "ALL=(ALL) NOPASSWD:ALL"
                        }
                    ]
                }
            }
        }
    }

    print('Deleting everything for cluster {}'.format(args.name))
    start = time.time()

    items = [cluster, kubeadmconfigtemplate]

    for item in items:
        result = namedtuple(item['kind'], 'group plural name')
        if item['kind'] == 'Cluster':
            kind = result(group=item['apiVersion'].split('/')[0], name=args.name,
                        plural=str.lower(item['kind'] + 's'))
            try:
                delete_crd(kind)
            except kubernetes.client.rest.ApiException:
                pass
        else:
            kind = result(group=item['apiVersion'].split('/')[0], name=clustername,
                          plural=str.lower(item['kind'] + 's'))
            try:
                delete_crd(kind)
            except kubernetes.client.rest.ApiException:
                pass

def create_cluster(args):
    """
    We should create the cluster without knowing too much about our vcenter!

    Ask vcenter:
        - datastore availables
        - remove hardcoded things use vcenter api
    """

    result = namedtuple('env', 'datastore network resourcepool server datacenter')
    clustername = args.name + '-md-0'

    """
    TODO: get this through pyvmomi based on which cluster we're
    """
    if args.env == 'lab':
        vm = result(datastore=args.datastore,
                    network=args.vlan,
                    resourcepool='*/Resources',
                    server=args.server,
                    datacenter=args.dc)

    cluster = {
        "apiVersion": "cluster.x-k8s.io/v1alpha3",
        "kind": "Cluster",
        "metadata": {
            "name": args.name,
            "namespace": "default"
        },
        "spec": {
            "clusterNetwork": {
                "pods": {
                    "cidrBlocks": [
                        "10.16.0.0/16"
                    ]
                }
            },
            "controlPlaneRef": {
                "apiVersion": "controlplane.cluster.x-k8s.io/v1alpha3",
                "kind": "KubeadmControlPlane",
                "name": args.name
            },
            "infrastructureRef": {
                "apiVersion": "infrastructure.cluster.x-k8s.io/v1alpha3",
                "kind": "VSphereCluster",
                "name": args.name
            }
        }
    }


    vspherecluster = {
        "apiVersion": "infrastructure.cluster.x-k8s.io/v1alpha3",
        "kind": "VSphereCluster",
        "metadata": {
            "name": args.name,
            "namespace": "default"
        },
        "spec": {
            "cloudProviderConfiguration": {
                "global": {
                    "insecure": True,
                    "secretName": "cloud-provider-vsphere-credentials",
                    "secretNamespace": "kube-system"
                },
                "network": {
                    "name": vm.network
                },
                "providerConfig": {
                    "cloud": {
                        "controllerImage": "gcr.io/cloud-provider-vsphere/cpi/release/manager:v1.2.0"
                    }
                },
                "virtualCenter": {
                    vm.server: {
                        "datacenters": vm.datacenter
                    }
                },
                "workspace": {
                    "datacenter": vm.datacenter,
                    "datastore": vm.datastore,
                    "folder": args.vmfolder,
                    "resourcePool": vm.resourcepool,
                    "server": vm.server
                }
            },
            "controlPlaneEndpoint": {
                "host": args.vip,
                "port": 6443
            },
            "server": vm.server
        }
    }

    vspheremachinetemplate = {
        "apiVersion": "infrastructure.cluster.x-k8s.io/v1alpha3",
        "kind": "VSphereMachineTemplate",
        "metadata": {
            "name": args.name,
            "namespace": "default"
        },
        "spec": {
            "template": {
                "spec": {
                    "cloneMode": "linkedClone",
                    "datacenter": vm.datacenter,
                    "datastore": vm.datastore,
                    "diskGiB": args.hd,
                    "folder": args.vmfolder,
                    "memoryMiB": args.ram,
                    "network": {
                        "devices": [
                            {
                                "dhcp4": True,
                                "networkName": vm.network
                            }
                        ]
                    },
                    "numCPUs": args.cpu,
                    "resourcePool": vm.resourcepool,
                    "server": vm.server,
                    "template": args.template
                }
            }
        }
    }
    content = '''apiVersion: v1\nkind: Pod\nmetadata:\n  creationTimestamp: null\n  name: kube-vip\n  namespace: kube-system\nspec:\n  containers:\n  - args:\n    - start\n    env:\n    - name: vip_arp\n      value: \"true\"\n    - name: vip_leaderelection\n      value: \"true\"\n    - name: vip_address\n      value: %s\n    - name: vip_interface\n      value: eth0\n    image: plndr/kube-vip:0.1.7\n    imagePullPolicy: IfNotPresent\n    name: kube-vip\n    resources: {}\n    securityContext:\n      capabilities:\n        add:\n        - NET_ADMIN\n        - SYS_TIME\n    volumeMounts:\n    - mountPath: /etc/kubernetes/admin.conf\n      name: kubeconfig\n  hostNetwork: true\n  volumes:\n  - hostPath:\n      path: /etc/kubernetes/admin.conf\n      type: FileOrCreate\n    name: kubeconfig\nstatus: {}\n''' % (args.vip)
    kubeadmcontrolplane = {
       "apiVersion": "controlplane.cluster.x-k8s.io/v1alpha3",
       "kind": "KubeadmControlPlane",
       "metadata": {
	  "name": args.name,
	  "namespace": "default"
       },
       "spec": {
	  "infrastructureTemplate": {
	     "apiVersion": "infrastructure.cluster.x-k8s.io/v1alpha3",
	     "kind": "VSphereMachineTemplate",
	     "name": args.name
	  },
	  "kubeadmConfigSpec": {
	     "clusterConfiguration": {
		"apiServer": {
		   "extraArgs": {
		      "cloud-provider": "external"
		   }
		},
		"controllerManager": {
		   "extraArgs": {
		      "cloud-provider": "external"
		   }
		}
	     },
	     "files": [
		{
		   "content": content,
		   "owner": "root:root",
		   "path": "/etc/kubernetes/manifests/kube-vip.yaml"
		}
	     ],
	     "initConfiguration": {
		"nodeRegistration": {
		   "criSocket": "/var/run/containerd/containerd.sock",
		   "kubeletExtraArgs": {
		      "cloud-provider": "external"
		   },
		   "name": "{{ ds.meta_data.hostname }}"
		}
	     },
	     "joinConfiguration": {
		"nodeRegistration": {
		   "criSocket": "/var/run/containerd/containerd.sock",
		   "kubeletExtraArgs": {
		      "cloud-provider": "external"
		   },
		   "name": "{{ ds.meta_data.hostname }}"
		}
	     },
	     "preKubeadmCommands": [
		"hostname \"{{ ds.meta_data.hostname }}\"",
		"echo \"::1         ipv6-localhost ipv6-loopback\" >/etc/hosts",
		"echo \"127.0.0.1   localhost\" >>/etc/hosts",
		"echo \"127.0.0.1   {{ ds.meta_data.hostname }}\" >>/etc/hosts",
		"echo \"{{ ds.meta_data.hostname }}\" >/etc/hostname"
	     ],
             "postKubeadmCommands": [
                "kubectl --kubeconfig /etc/kubernetes/admin.conf apply -f https://docs.projectcalico.org/manifests/calico.yaml",
                "kubectl --kubeconfig /etc/kubernetes/admin.conf apply -f https://gist.githubusercontent.com/pathcl/ccc85ea078d42b9489557e13438670f7/raw/48d8cf3e4aca636dda1dce46e5ecd695bb816566/ingress-nginx.yml"
             ],
	     "useExperimentalRetryJoin": True,
	     "users": [
		{
		   "name": "sysop",
		   "sshAuthorizedKeys": [
		      "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCoJKZ7dZJVV3+U6zXRvvQSyFeM2QXgfK/CyboGsPvi/ApNk7HpGNg+ws1FTYlDeztgsecfsgkmNgsKv6X+zaBB3ljy7HGlqZs2JSzbVT1/CKQ7m3ZQssHykFYOBVrTHO9+PzBaYhgosU8DqT/joId3mk+G2QnaXr0e6oYd9P8df101c9EOCZyg9oZ2t3TEotPQE2gMwInnDX1NXF/w+xDWOzRU7E+1cwZusuPtXPgXQdlheHOQ4pi+obx/f3Ur8DRURNe68cof1d+ByaYCDWQCONqyzCCRXzkpOX1ZULL2PSj5quXkpaA/ZRdxTQuonXvKTCcUsAC1BYwvMeYtrlQN pathcl@kepler"
		   ],
		   "sudo": "ALL=(ALL) NOPASSWD:ALL"
		}
	     ]
	  },
	  "replicas": args.masters,
	  "version": args.release
       }
    }



    kct = {
       "apiVersion": "bootstrap.cluster.x-k8s.io/v1alpha3",
       "kind": "KubeadmConfigTemplate",
       "metadata": {
          "name": clustername,
          "namespace": "default"
       },
       "spec": {
          "template": {
             "spec": {
                "joinConfiguration": {
                   "nodeRegistration": {
                      "criSocket": "/var/run/containerd/containerd.sock",
                      "kubeletExtraArgs": {
                         "cloud-provider": "external"
                      },
                      "name": "{{ ds.meta_data.hostname }}"
                   }
                },
                "preKubeadmCommands": [
                   "hostname \"{{ ds.meta_data.hostname }}\"",
                   "echo \"::1         ipv6-localhost ipv6-loopback\" >/etc/hosts",
                   "echo \"127.0.0.1   localhost\" >>/etc/hosts",
                   "echo \"127.0.0.1   {{ ds.meta_data.hostname }}\" >>/etc/hosts",
                   "echo \"{{ ds.meta_data.hostname }}\" >/etc/hostname"
                ],
                "users": [
                   {
                      "name": "sysop",
                      "sshAuthorizedKeys": [
                         "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCoJKZ7dZJVV3+U6zXRvvQSyFeM2QXgfK/CyboGsPvi/ApNk7HpGNg+ws1FTYlDeztgsecfsgkmNgsKv6X+zaBB3ljy7HGlqZs2JSzbVT1/CKQ7m3ZQssHykFYOBVrTHO9+PzBaYhgosU8DqT/joId3mk+G2QnaXr0e6oYd9P8df101c9EOCZyg9oZ2t3TEotPQE2gMwInnDX1NXF/w+xDWOzRU7E+1cwZusuPtXPgXQdlheHOQ4pi+obx/f3Ur8DRURNe68cof1d+ByaYCDWQCONqyzCCRXzkpOX1ZULL2PSj5quXkpaA/ZRdxTQuonXvKTCcUsAC1BYwvMeYtrlQN pathcl@kepler"
                      ],
                      "sudo": "ALL=(ALL) NOPASSWD:ALL"
                   }
                ]
             }
          }
       }
    }



    machinedeployment = {
        "apiVersion": "cluster.x-k8s.io/v1alpha3",
        "kind": "MachineDeployment",
        "metadata": {
            "labels": {
                "cluster.x-k8s.io/cluster-name": args.name
            },
            "name": clustername,
            "namespace": "default"
        },
        "spec": {
            "clusterName": args.name,
            "replicas": args.workers,
            "selector": {
                "matchLabels": {
                    "cluster.x-k8s.io/cluster-name": args.name
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "cluster.x-k8s.io/cluster-name": args.name
                    }
                },
                "spec": {
                    "bootstrap": {
                        "configRef": {
                            "apiVersion": "bootstrap.cluster.x-k8s.io/v1alpha3",
                            "kind": "KubeadmConfigTemplate",
                            "name": clustername
                        }
                    },
                    "clusterName": args.name,
                    "infrastructureRef": {
                        "apiVersion": "infrastructure.cluster.x-k8s.io/v1alpha3",
                        "kind": "VSphereMachineTemplate",
                        "name": args.name
                    },
                    "version": args.release
                }
            }
        }
    }

    clusterresourceset = {
       "apiVersion": "addons.cluster.x-k8s.io/v1alpha3",
       "kind": "ClusterResourceSet",
       "metadata": {
          "labels": {
             "cluster.x-k8s.io/cluster-name": "lab01"
          },
          "name": "lab01-crs-0",
          "namespace": "default"
       },
       "spec": {
          "clusterSelector": {
             "matchLabels": {
                "cluster.x-k8s.io/cluster-name": "lab01"
             }
          },
          "resources": [
             {
                "kind": "Secret",
                "name": "vsphere-csi-controller"
             },
             {
                "kind": "ConfigMap",
                "name": "vsphere-csi-controller-role"
             },
             {
                "kind": "ConfigMap",
                "name": "vsphere-csi-controller-binding"
             },
             {
                "kind": "Secret",
                "name": "csi-vsphere-config"
             },
             {
                "kind": "ConfigMap",
                "name": "csi.vsphere.vmware.com"
             },
             {
                "kind": "ConfigMap",
                "name": "vsphere-csi-node"
             },
             {
                "kind": "ConfigMap",
                "name": "vsphere-csi-controller"
             }
          ]
       }
    }


    deployed_clusters = list_clusters()
    if args.name in deployed_clusters:
        sys.exit('{} already taken please choose another name\n'.format(args.name))

    start = time.time()
    items = [cluster, kct, kubeadmcontrolplane, machinedeployment, vspherecluster, vspheremachinetemplate, clusterresourceset]

    for item in items:
        result = namedtuple(item['kind'], 'group plural body')
        kind = result(group=item['apiVersion'].split('/')[0],
                        plural=str.lower(item['kind'] + 's'), body=item)
        try:
            create_crd(kind)
        except:
            print('Error creating {}'.format(item))
    yaml = '''
---
apiVersion: v1
kind: Secret
metadata:
  name: vsphere-csi-controller
  namespace: default
stringData:
  data: |
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: vsphere-csi-controller
      namespace: kube-system
type: addons.cluster.x-k8s.io/resource-set
---
apiVersion: v1
data:
  data: |
    apiVersion: rbac.authorization.k8s.io/v1
    kind: ClusterRole
    metadata:
      name: vsphere-csi-controller-role
    rules:
    - apiGroups:
      - storage.k8s.io
      resources:
      - csidrivers
      verbs:
      - create
      - delete
    - apiGroups:
      - ""
      resources:
      - nodes
      - pods
      - secrets
      verbs:
      - get
      - list
      - watch
    - apiGroups:
      - ""
      resources:
      - persistentvolumes
      verbs:
      - get
      - list
      - watch
      - update
      - create
      - delete
      - patch
    - apiGroups:
      - storage.k8s.io
      resources:
      - volumeattachments
      verbs:
      - get
      - list
      - watch
      - update
      - patch
    - apiGroups:
      - ""
      resources:
      - persistentvolumeclaims
      verbs:
      - get
      - list
      - watch
      - update
    - apiGroups:
      - storage.k8s.io
      resources:
      - storageclasses
      - csinodes
      verbs:
      - get
      - list
      - watch
    - apiGroups:
      - ""
      resources:
      - events
      verbs:
      - list
      - watch
      - create
      - update
      - patch
    - apiGroups:
      - coordination.k8s.io
      resources:
      - leases
      verbs:
      - get
      - watch
      - list
      - delete
      - update
      - create
    - apiGroups:
      - snapshot.storage.k8s.io
      resources:
      - volumesnapshots
      verbs:
      - get
      - list
    - apiGroups:
      - snapshot.storage.k8s.io
      resources:
      - volumesnapshotcontents
      verbs:
      - get
      - list
kind: ConfigMap
metadata:
  name: vsphere-csi-controller-role
  namespace: default
---
apiVersion: v1
data:
  data: |
    apiVersion: rbac.authorization.k8s.io/v1
    kind: ClusterRoleBinding
    metadata:
      name: vsphere-csi-controller-binding
    roleRef:
      apiGroup: rbac.authorization.k8s.io
      kind: ClusterRole
      name: vsphere-csi-controller-role
    subjects:
    - kind: ServiceAccount
      name: vsphere-csi-controller
      namespace: kube-system
kind: ConfigMap
metadata:
  name: vsphere-csi-controller-binding
  namespace: default
---
apiVersion: v1
kind: Secret
metadata:
  name: csi-vsphere-config
  namespace: default
stringData:
  data: |
    apiVersion: v1
    kind: Secret
    metadata:
      name: csi-vsphere-config
      namespace: kube-system
    stringData:
      csi-vsphere.conf: |+
        [Global]
        insecure-flag = true
        cluster-id = "%s"

        [VirtualCenter "%s"]
        user = "%s"
        password = "%s"
        datacenters = "%s"

        [Network]
        public-network = "%s"

    type: Opaque
type: addons.cluster.x-k8s.io/resource-set
---
apiVersion: v1
data:
  data: |
    apiVersion: storage.k8s.io/v1
    kind: CSIDriver
    metadata:
      name: csi.vsphere.vmware.com
    spec:
      attachRequired: true
kind: ConfigMap
metadata:
  name: csi.vsphere.vmware.com
  namespace: default
---
apiVersion: v1
data:
  data: |
    apiVersion: apps/v1
    kind: DaemonSet
    metadata:
      name: vsphere-csi-node
      namespace: kube-system
    spec:
      selector:
        matchLabels:
          app: vsphere-csi-node
      template:
        metadata:
          labels:
            app: vsphere-csi-node
            role: vsphere-csi
        spec:
          containers:
          - args:
            - --v=5
            - --csi-address=$(ADDRESS)
            - --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH)
            env:
            - name: ADDRESS
              value: /csi/csi.sock
            - name: DRIVER_REG_SOCK_PATH
              value: /var/lib/kubelet/plugins/csi.vsphere.vmware.com/csi.sock
            image: quay.io/k8scsi/csi-node-driver-registrar:v1.2.0
            lifecycle:
              preStop:
                exec:
                  command:
                  - /bin/sh
                  - -c
                  - rm -rf /registration/csi.vsphere.vmware.com-reg.sock /csi/csi.sock
            name: node-driver-registrar
            resources: {}
            securityContext:
              privileged: true
            volumeMounts:
            - mountPath: /csi
              name: plugin-dir
            - mountPath: /registration
              name: registration-dir
          - env:
            - name: CSI_ENDPOINT
              value: unix:///csi/csi.sock
            - name: X_CSI_MODE
              value: node
            - name: X_CSI_SPEC_REQ_VALIDATION
              value: "false"
            - name: VSPHERE_CSI_CONFIG
              value: /etc/cloud/csi-vsphere.conf
            - name: LOGGER_LEVEL
              value: PRODUCTION
            - name: X_CSI_LOG_LEVEL
              value: INFO
            - name: NODE_NAME
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
            image: gcr.io/cloud-provider-vsphere/csi/release/driver:v2.0.0
            livenessProbe:
              failureThreshold: 3
              httpGet:
                path: /healthz
                port: healthz
              initialDelaySeconds: 10
              periodSeconds: 5
              timeoutSeconds: 3
            name: vsphere-csi-node
            ports:
            - containerPort: 9808
              name: healthz
              protocol: TCP
            resources: {}
            securityContext:
              allowPrivilegeEscalation: true
              capabilities:
                add:
                - SYS_ADMIN
              privileged: true
            volumeMounts:
            - mountPath: /etc/cloud
              name: vsphere-config-volume
            - mountPath: /csi
              name: plugin-dir
            - mountPath: /var/lib/kubelet
              mountPropagation: Bidirectional
              name: pods-mount-dir
            - mountPath: /dev
              name: device-dir
          - args:
            - --csi-address=/csi/csi.sock
            image: quay.io/k8scsi/livenessprobe:v1.1.0
            name: liveness-probe
            resources: {}
            volumeMounts:
            - mountPath: /csi
              name: plugin-dir
          dnsPolicy: Default
          tolerations:
          - effect: NoSchedule
            operator: Exists
          - effect: NoExecute
            operator: Exists
          volumes:
          - name: vsphere-config-volume
            secret:
              secretName: csi-vsphere-config
          - hostPath:
              path: /var/lib/kubelet/plugins_registry
              type: Directory
            name: registration-dir
          - hostPath:
              path: /var/lib/kubelet/plugins/csi.vsphere.vmware.com/
              type: DirectoryOrCreate
            name: plugin-dir
          - hostPath:
              path: /var/lib/kubelet
              type: Directory
            name: pods-mount-dir
          - hostPath:
              path: /dev
            name: device-dir
      updateStrategy:
        type: RollingUpdate
kind: ConfigMap
metadata:
  name: vsphere-csi-node
  namespace: default
---
apiVersion: v1
data:
  data: |
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: vsphere-csi-controller
      namespace: kube-system
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: vsphere-csi-controller
      strategy:
        type: RollingUpdate
      template:
        metadata:
          labels:
            app: vsphere-csi-controller
            role: vsphere-csi
        spec:
          containers:
          - args:
            - --v=4
            - --timeout=300s
            - --csi-address=$(ADDRESS)
            - --leader-election
            env:
            - name: ADDRESS
              value: /csi/csi.sock
            image: quay.io/k8scsi/csi-attacher:v2.0.0
            name: csi-attacher
            resources: {}
            volumeMounts:
            - mountPath: /csi
              name: socket-dir
          - env:
            - name: CSI_ENDPOINT
              value: unix:///var/lib/csi/sockets/pluginproxy/csi.sock
            - name: X_CSI_MODE
              value: controller
            - name: VSPHERE_CSI_CONFIG
              value: /etc/cloud/csi-vsphere.conf
            - name: LOGGER_LEVEL
              value: PRODUCTION
            - name: X_CSI_LOG_LEVEL
              value: INFO
            image: gcr.io/cloud-provider-vsphere/csi/release/driver:v2.0.0
            lifecycle:
              preStop:
                exec:
                  command:
                  - /bin/sh
                  - -c
                  - rm -rf /var/lib/csi/sockets/pluginproxy/csi.vsphere.vmware.com
            livenessProbe:
              failureThreshold: 3
              httpGet:
                path: /healthz
                port: healthz
              initialDelaySeconds: 10
              periodSeconds: 5
              timeoutSeconds: 3
            name: vsphere-csi-controller
            ports:
            - containerPort: 9808
              name: healthz
              protocol: TCP
            resources: {}
            volumeMounts:
            - mountPath: /etc/cloud
              name: vsphere-config-volume
              readOnly: true
            - mountPath: /var/lib/csi/sockets/pluginproxy/
              name: socket-dir
          - args:
            - --csi-address=$(ADDRESS)
            env:
            - name: ADDRESS
              value: /var/lib/csi/sockets/pluginproxy/csi.sock
            image: quay.io/k8scsi/livenessprobe:v1.1.0
            name: liveness-probe
            resources: {}
            volumeMounts:
            - mountPath: /var/lib/csi/sockets/pluginproxy/
              name: socket-dir
          - args:
            - --leader-election
            env:
            - name: X_CSI_FULL_SYNC_INTERVAL_MINUTES
              value: "30"
            - name: LOGGER_LEVEL
              value: PRODUCTION
            - name: VSPHERE_CSI_CONFIG
              value: /etc/cloud/csi-vsphere.conf
            image: gcr.io/cloud-provider-vsphere/csi/release/syncer:v2.0.0
            name: vsphere-syncer
            resources: {}
            volumeMounts:
            - mountPath: /etc/cloud
              name: vsphere-config-volume
              readOnly: true
          - args:
            - --v=4
            - --timeout=300s
            - --csi-address=$(ADDRESS)
            - --feature-gates=Topology=true
            - --strict-topology
            - --enable-leader-election
            - --leader-election-type=leases
            env:
            - name: ADDRESS
              value: /csi/csi.sock
            image: quay.io/k8scsi/csi-provisioner:v1.4.0
            name: csi-provisioner
            resources: {}
            volumeMounts:
            - mountPath: /csi
              name: socket-dir
          dnsPolicy: Default
          serviceAccountName: vsphere-csi-controller
          tolerations:
          - effect: NoSchedule
            key: node-role.kubernetes.io/master
            operator: Exists
          volumes:
          - name: vsphere-config-volume
            secret:
              secretName: csi-vsphere-config
          - hostPath:
              path: /var/lib/csi/sockets/pluginproxy/csi.vsphere.vmware.com
              type: DirectoryOrCreate
            name: socket-dir
kind: ConfigMap
metadata:
  name: vsphere-csi-controller
  namespace: default
    ''' % ("default/" + args.name, args.server,  args.username, args.password, args.dc, args.vlan)


    fd, path = mkstemp()
    with open(fd, 'w') as f:
        f.write(yaml)
    k8s_client = client.api_client.ApiClient()

    try:
        create_from_yaml(yaml_file=path,
                        k8s_client=k8s_client, verbose=False)
    except Exception as e:
        print(str(e))

def list_clusters():
    config.load_kube_config()
    api = client.CustomObjectsApi()
    clusters = []
    q = api.list_namespaced_custom_object(
        namespace="default",
        group="cluster.x-k8s.io",
        version="v1alpha3",
        plural="clusters",
    )
    for item in q.items():
        if isinstance(item[1], list):
            for item in item[1]:
                clusters.append(item['metadata']['name'])

    return clusters

def upgrade_cluster(args):
    # ideal steps:
    # - check what's the version currently running and only upgrade if new release
    # - create/look for a new vspheremachinetemplate
    # - replace kcp spec with new template
    # - find out which images are available to upgrade
    # - what if vspheremachinetemplate already exists ?
    #    - check versions available
    #    - maybe we can do it daily only need to compare

    oinfo = namedtuple('Cluster', 'group plural name')
    cinfo = oinfo(group='cluster.x-k8s.io',
            plural='clusters', name=args.name)
    info = info_crd(cinfo)

    upgrade_name_kcp = args.name + "-upgrade"
    upgrade_name_md = args.name + "-md-0"

    yaml = {
    "apiVersion": "infrastructure.cluster.x-k8s.io/v1alpha3",
    "kind": "VSphereMachineTemplate",
    "metadata": {
    "name": upgrade_name_kcp,
    "namespace": "default",
    "ownerReferences": [
        {
            "apiVersion": "cluster.x-k8s.io/v1alpha3",
            "kind": "Cluster",
            "name": args.name,
            "uid": info[1]
        }
    ]
    },
    "spec": {
    "template": {
        "spec": {
            "cloneMode": "linkedClone",
            "datacenter": args.dc,
            "datastore": args.datastore,
            "diskGiB": 80,
            "folder": args.vmfolder,
            "memoryMiB": 8192,
            "network": {
            "devices": [
                {
                    "dhcp4": True,
                    "networkName": args.vlan
                }
            ]
            },
            "numCPUs": 4,
            "resourcePool": "*/Resources",
            "server": args.server,
            "template": args.template
            }
        }
    }
    }
    obj = namedtuple('vspheremachinetemplate', 'group plural body name')
    vmtemplate = obj(group='infrastructure.cluster.x-k8s.io',
            plural='vspheremachinetemplates', body=yaml, name=upgrade_name_kcp)

    # print('We created vspheremachinetemplate')
    try:
        create_crd(vmtemplate)
    except kubernetes.client.rest.ApiException:
        # we shouldn't do this
        pass

    ## apply patch master nodes
    # we should find a way to patch kcp/md objects
    # manual steps for controlplane/dataplane
    # controlplane:
    #   - kaas.py upgrade -n lab -t centos-7-kube-v1.18.5 |k apply -f - 
    # dataplane: 
    #   -  k edit machinedeployment lab-md-0
    #     - change reference to infrastructureRef.name && spec.version

    json_kcp = {
    "spec": {
        "infrastructureTemplate": {
            "apiVersion": "infrastructure.cluster.x-k8s.io/v1alpha3",
            "kind": "VSphereMachineTemplate",
            "name": upgrade_name_kcp,
            "namespace": "default"
        }
    }
    }
    objc = namedtuple('kubeadmcontrolplane', 'group plural body name')
    controlplane = objc(group='controlplane.cluster.x-k8s.io',
                        plural='kubeadmcontrolplanes', body=json_kcp, name=args.name)

    patch_crd(controlplane)

    ## apply patch worker nodes
    json_md = {
        "spec": {
            "template": {
                "spec": {
                    "infrastructureRef": {
                        "apiVersion": "infrastructure.cluster.x-k8s.io/v1alpha3",
                        "kind": "VSphereMachineTemplate",
                        "name": upgrade_name_kcp
                    },
                    "version": args.upgrade
                }
            }
        }
    }
    
    objd = namedtuple('machinedeployment', 'group plural body name')
    dataplane = objd(group='cluster.x-k8s.io',
                     plural='machinedeployments', body=json_md, name=upgrade_name_md)
    patch_crd(dataplane)


def get_kubeconfig(args):
    k8s_config = config.load_kube_config()
    k8s_client = client.api_client.ApiClient(configuration=k8s_config)
    api_instance = kubernetes.client.CoreV1Api(k8s_client)

    name = '%s-kubeconfig' % (args.name)
    namespace = 'default'

    try:
        api_response = api_instance.read_namespaced_secret(name, namespace, pretty=True, exact=True, export=True)
        print(b64decode(str.encode(api_response.data['value'])).decode("utf-8"))
    except ApiException as e:
        print("Exception when calling CoreV1Api->read_namespaced_secret: %s\n" % e)


def addons(args):
    #  its yaml time !
    # 
    # - create ns
    # - deploy nginx-controller
    # - deploy kubernetes-ingress-dashboard
    yaml = '''
---
apiVersion: v1
kind: Namespace
metadata:
  name: ingress-nginx
---
apiVersion: v1
kind: Namespace
metadata:
  name: kubernetes-dashboard-head
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: kube-dashboard
  namespace: kubernetes-dashboard-head
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: kubernetes-dashboard-head
    namespace: kubernetes-dashboard-head 
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: tiller
  namespace: kube-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: tiller
    namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: hyperion
  namespace: kube-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: Group
    name: Some-Ldap_group-Here
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: system:aggregated-metrics-reader
  labels:
    rbac.authorization.k8s.io/aggregate-to-view: "true"
    rbac.authorization.k8s.io/aggregate-to-edit: "true"
    rbac.authorization.k8s.io/aggregate-to-admin: "true"
rules:
- apiGroups: ["metrics.k8s.io"]
  resources: ["pods", "nodes"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: metrics-server:system:auth-delegator
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:auth-delegator
subjects:
- kind: ServiceAccount
  name: metrics-server
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: metrics-server-auth-reader
  namespace: kube-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: extension-apiserver-authentication-reader
subjects:
- kind: ServiceAccount
  name: metrics-server
  namespace: kube-system
---
apiVersion: apiregistration.k8s.io/v1beta1
kind: APIService
metadata:
  name: v1beta1.metrics.k8s.io
spec:
  service:
    name: metrics-server
    namespace: kube-system
  group: metrics.k8s.io
  version: v1beta1
  insecureSkipTLSVerify: true
  groupPriorityMinimum: 100
  versionPriority: 100
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: metrics-server
  namespace: kube-system
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tiller
  namespace: kube-system
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: metrics-server
  namespace: kube-system
  labels:
    k8s-app: metrics-server
spec:
  selector:
    matchLabels:
      k8s-app: metrics-server
  template:
    metadata:
      name: metrics-server
      labels:
        k8s-app: metrics-server
    spec:
      serviceAccountName: metrics-server
      volumes:
      # mount in tmp so we can safely use from-scratch images and/or read-only containers
      - name: tmp-dir
        emptyDir: {}
      containers:
      - name: metrics-server
        image: k8s.gcr.io/metrics-server-amd64:v0.3.6
        imagePullPolicy: IfNotPresent
        args:
          - --kubelet-preferred-address-types=InternalIP
          - --kubelet-insecure-tls          
          - --cert-dir=/tmp
          - --secure-port=4443
        ports:
        - name: main-port
          containerPort: 4443
          protocol: TCP
        securityContext:
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 1000
        volumeMounts:
        - name: tmp-dir
          mountPath: /tmp
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: "amd64"
---
apiVersion: v1
kind: Service
metadata:
  name: metrics-server
  namespace: kube-system
  labels:
    kubernetes.io/name: "Metrics-server"
    kubernetes.io/cluster-service: "true"
spec:
  selector:
    k8s-app: metrics-server
  ports:
  - port: 443
    protocol: TCP
    targetPort: main-port
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: system:metrics-server
rules:
- apiGroups:
  - ""
  resources:
  - pods
  - nodes
  - nodes/stats
  - namespaces
  - configmaps
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: system:metrics-server
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:metrics-server
subjects:
- kind: ServiceAccount
  name: metrics-server
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRole
metadata:
  name: ingress-nginx
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
rules:
  - apiGroups: [""]
    resources: ["configmaps", "endpoints", "nodes", "pods", "secrets"]
    verbs: ["list", "watch"]
  - apiGroups: [""]
    resources: ["nodes"]
    verbs: ["get"]
  - apiGroups: [""]
    resources: ["services"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["extensions","networking.k8s.io"]
    resources: ["ingresses"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["create", "patch"]
  - apiGroups: ["extensions","networking.k8s.io"]
    resources: ["ingresses/status"]
    verbs: ["update"]
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: ingress-nginx
  namespace: ingress-nginx
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: ingress-nginx
subjects:
  - kind: ServiceAccount
    name: ingress-nginx
    namespace: ingress-nginx
---
apiVersion: v1
items:
- apiVersion: v1
  kind: ConfigMap
  metadata:
    name: ingress-controller-leader-nginx
    namespace: ingress-nginx
- apiVersion: v1
  data:
    proxy-hide-headers: Server
    server-tokens: "False"
  kind: ConfigMap
  metadata:
    labels:
      app.kubernetes.io/name: ingress-nginx
      app.kubernetes.io/part-of: ingress-nginx
    name: ingress-nginx
    namespace: ingress-nginx
- apiVersion: v1
  kind: ConfigMap
  metadata:
    labels:
      app.kubernetes.io/name: ingress-nginx
      app.kubernetes.io/part-of: ingress-nginx
    name: tcp-services
    namespace: ingress-nginx
- apiVersion: v1
  kind: ConfigMap
  metadata:
    labels:
      app.kubernetes.io/name: ingress-nginx
      app.kubernetes.io/part-of: ingress-nginx
    name: udp-services
    namespace: ingress-nginx
kind: List
metadata:
  resourceVersion: ""
  selfLink: ""
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: ingress-nginx-controller
  namespace: ingress-nginx
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: ingress-nginx
      app.kubernetes.io/part-of: ingress-nginx
  template:
    metadata:
      labels:
        app.kubernetes.io/name: ingress-nginx
        app.kubernetes.io/part-of: ingress-nginx
      annotations:
        prometheus.io/port: "10254"
        prometheus.io/scrape: "true"
    spec:
      serviceAccountName: ingress-nginx
      hostNetwork: true
      dnsPolicy: ClusterFirstWithHostNet
      containers:
        - name: ingress-nginx-controller
          image: quay.io/kubernetes-ingress-controller/nginx-ingress-controller:0.30.0
          imagePullPolicy: Always
          args:
            - /nginx-ingress-controller
            - --configmap=$(POD_NAMESPACE)/ingress-nginx
            - --tcp-services-configmap=$(POD_NAMESPACE)/tcp-services
            - --udp-services-configmap=$(POD_NAMESPACE)/udp-services
            - --annotations-prefix=nginx.ingress.kubernetes.io
            - --report-node-internal-ip-address
          securityContext:
            allowPrivilegeEscalation: true
            capabilities:
                drop:
                  - ALL
                add:
                  - NET_BIND_SERVICE
            runAsUser: 101
          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
          ports:
            - name: http
              containerPort: 80
              hostPort: 80
            - name: https
              containerPort: 443
              hostPort: 443
          livenessProbe:
            failureThreshold: 3
            httpGet:
              path: /healthz
              port: 10254
              scheme: HTTP
            initialDelaySeconds: 5
            timeoutSeconds: 5
            successThreshold: 1
            failureThreshold: 10
          readinessProbe:
            failureThreshold: 3
            httpGet:
              path: /healthz
              port: 10254
              scheme: HTTP
            timeoutSeconds: 5
            successThreshold: 1
            failureThreshold: 10
---
apiVersion: v1
items:
- apiVersion: rbac.authorization.k8s.io/v1
  kind: Role
  metadata:
    labels:
      app.kubernetes.io/name: ingress-nginx
      app.kubernetes.io/part-of: ingress-nginx
    name: ingress-nginx
    namespace: ingress-nginx
  rules:
  - apiGroups:
    - ""
    resources:
    - configmaps
    - pods
    - secrets
    - namespaces
    verbs:
    - get
  - apiGroups:
    - ""
    resourceNames:
    - ingress-controller-leader-nginx
    resources:
    - configmaps
    verbs:
    - get
    - update
  - apiGroups:
    - ""
    resources:
    - configmaps
    verbs:
    - create
  - apiGroups:
    - ""
    resources:
    - endpoints
    verbs:
    - get
  - apiGroups:
    - policy
    resourceNames:
    - ingress-nginx
    resources:
    - podsecuritypolicies
    verbs:
    - use
kind: List
metadata:
  resourceVersion: ""
  selfLink: ""
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: RoleBinding
metadata:
  name: ingress-nginx
  namespace: ingress-nginx
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: ingress-nginx
subjects:
  - kind: ServiceAccount
    name: ingress-nginx
    namespace: ingress-nginx
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ingress-nginx
  namespace: ingress-nginx
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
---
apiVersion: v1
kind: ServiceAccount
metadata:
  labels:
    k8s-app: kubernetes-dashboard-head
  name: kubernetes-dashboard-head
  namespace: kubernetes-dashboard-head
---
kind: Service
apiVersion: v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard-head
  name: kubernetes-dashboard-head
  namespace: kubernetes-dashboard-head
spec:
  ports:
    - port: 443
      targetPort: 8443
  selector:
    k8s-app: kubernetes-dashboard-head
---
apiVersion: v1
kind: Secret
metadata:
  labels:
    k8s-app: kubernetes-dashboard-head
  name: kubernetes-dashboard-csrf
  namespace: kubernetes-dashboard-head
type: Opaque
data:
  csrf: ""
---
apiVersion: v1
kind: Secret
metadata:
  labels:
    k8s-app: kubernetes-dashboard-head
  name: kubernetes-dashboard-key-holder
  namespace: kubernetes-dashboard-head
type: Opaque
---
kind: ConfigMap
apiVersion: v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard-head
  name: kubernetes-dashboard-settings
  namespace: kubernetes-dashboard-head
---
kind: Role
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard-head
  name: kubernetes-dashboard-head
  namespace: kubernetes-dashboard-head
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames: ["kubernetes-dashboard-key-holder", "kubernetes-dashboard-certs", "kubernetes-dashboard-csrf"]
    verbs: ["get", "update", "delete"]
  - apiGroups: [""]
    resources: ["configmaps"]
    resourceNames: ["kubernetes-dashboard-settings"]
    verbs: ["get", "update"]
  - apiGroups: [""]
    resources: ["services"]
    resourceNames: ["heapster", "dashboard-metrics-scraper-head"]
    verbs: ["proxy"]
  - apiGroups: [""]
    resources: ["services/proxy"]
    resourceNames: ["heapster", "http:heapster:", "https:heapster:", "dashboard-metrics-scraper-head", "http:dashboard-metrics-scraper-head"]
    verbs: ["get"]
---
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard-head
  name: kubernetes-dashboard-head
rules:
  # Allow Metrics Scraper to get metrics from the Metrics server
  - apiGroups: ["metrics.k8s.io"]
    resources: ["pods", "nodes"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  labels:
    k8s-app: kubernetes-dashboard-head
  name: kubernetes-dashboard-head
  namespace: kubernetes-dashboard-head
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: kubernetes-dashboard-head
subjects:
  - kind: ServiceAccount
    name: kubernetes-dashboard-head
    namespace: kubernetes-dashboard-head
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kubernetes-dashboard-head
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kubernetes-dashboard-head
subjects:
  - kind: ServiceAccount
    name: kubernetes-dashboard-head
    namespace: kubernetes-dashboard-head
---
kind: Deployment
apiVersion: apps/v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard-head
  name: kubernetes-dashboard-head
  namespace: kubernetes-dashboard-head
spec:
  replicas: 1
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      k8s-app: kubernetes-dashboard-head
  template:
    metadata:
      labels:
        k8s-app: kubernetes-dashboard-head
    spec:
      containers:
        - name: kubernetes-dashboard-head
          image: kubernetesdashboarddev/dashboard:head
          ports:
            - containerPort: 9090
              protocol: TCP
          args:
            - --namespace=kubernetes-dashboard-head
          volumeMounts:
            # Create on-disk volume to store exec logs
            - mountPath: /tmp
              name: tmp-volume
          livenessProbe:
            httpGet:
              path: /
              port: 9090
            initialDelaySeconds: 30
            timeoutSeconds: 30
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsUser: 1001
            runAsGroup: 2001
      volumes:
        - name: tmp-volume
          emptyDir: {}
      serviceAccountName: kubernetes-dashboard-head
      nodeSelector:
        "beta.kubernetes.io/os": linux
      tolerations:
        - key: node-role.kubernetes.io/master
          effect: NoSchedule
---
kind: Service
apiVersion: v1
metadata:
  labels:
    k8s-app: dashboard-metrics-scraper-head
  name: dashboard-metrics-scraper-head
  namespace: kubernetes-dashboard-head
spec:
  ports:
    - port: 8000
      targetPort: 8000
  selector:
    k8s-app: dashboard-metrics-scraper-head
---
kind: Deployment
apiVersion: apps/v1
metadata:
  labels:
    k8s-app: dashboard-metrics-scraper-head
  name: dashboard-metrics-scraper-head
  namespace: kubernetes-dashboard-head
spec:
  replicas: 1
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      k8s-app: dashboard-metrics-scraper-head
  template:
    metadata:
      labels:
        k8s-app: dashboard-metrics-scraper-head
      annotations:
        seccomp.security.alpha.kubernetes.io/pod: 'runtime/default'
    spec:
      containers:
        - name: dashboard-metrics-scraper-head
          image: kubernetesdashboarddev/dashboard-metrics-sidecar:latest
          ports:
            - containerPort: 8000
              protocol: TCP
          livenessProbe:
            httpGet:
              scheme: HTTP
              path: /
              port: 8000
            initialDelaySeconds: 30
            timeoutSeconds: 30
          volumeMounts:
          - mountPath: /tmp
            name: tmp-volume
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsUser: 1001
            runAsGroup: 2001
      serviceAccountName: kubernetes-dashboard-head
      nodeSelector:
        "beta.kubernetes.io/os": linux
      tolerations:
        - key: node-role.kubernetes.io/master
          effect: NoSchedule
      volumes:
        - name: tmp-volume
          emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  labels:
    k8s-app: kubernetes-dashboard-head
  name: kubernetes-dashboard
  namespace: kubernetes-dashboard-head
spec:
  ports:
  - name: http
    port: 80
    protocol: TCP
    targetPort: 9090
  selector:
    k8s-app: kubernetes-dashboard-head
  sessionAffinity: None
  type: ClusterIP
status: {}
'''


    fd, path = mkstemp()
    kubeconfig = os.getcwd() + '/kubeconfig'
    with open(fd, 'w') as f:
        f.write(yaml)
    k8s_config = config.load_kube_config(
        config_file=kubeconfig)
    k8s_client = client.api_client.ApiClient(configuration=k8s_config)

    try:
        print(path)
        # create_from_yaml(yaml_file=path,
        #                 k8s_client=k8s_client, verbose=False)
    except Exception as e:
        print(str(e))

def scale_cluster(args):
  name = '%s-md-0' % args.name

  oinfo = namedtuple('MachineDeployment', 'group plural name')
  cinfo = oinfo(group='cluster.x-k8s.io',
                plural='machinedeployments', name=name)

  info = info_crd(cinfo)

  yaml = {
      "apiVersion": "cluster.x-k8s.io/v1alpha3",
      "kind": "MachineDeployment",
      "metadata": {
          "generation": 1,
          "resourceVersion": info[0],
          "labels": {
              "cluster.x-k8s.io/cluster-name": args.name
          },
          "name": name,
          "namespace": "default",
          "ownerReferences": [
              {
                  "apiVersion": "cluster.x-k8s.io/v1alpha3",
                  "kind": "Cluster",
                  "name": args.name,
                  "uid": info[1]
              }
          ]
      },
      "spec": {
          "clusterName": args.name,
          "minReadySeconds": 0,
          "progressDeadlineSeconds": 600,
          "replicas": args.workers,
          "revisionHistoryLimit": 1,
          "selector": {
              "matchLabels": {
                  "cluster.x-k8s.io/cluster-name": args.name
              }
          },
          "strategy": {
              "rollingUpdate": {
                  "maxSurge": 1,
                  "maxUnavailable": 0
              },
              "type": "RollingUpdate"
          },
          "template": {
              "metadata": {
                  "labels": {
                      "cluster.x-k8s.io/cluster-name": args.name
                  }
              },
              "spec": {
                  "bootstrap": {
                      "configRef": {
                          "apiVersion": "bootstrap.cluster.x-k8s.io/v1alpha3",
                          "kind": "KubeadmConfigTemplate",
                          "name": name
                      }
                  },
                  "clusterName": args.name,
                  "infrastructureRef": {
                      "apiVersion": "infrastructure.cluster.x-k8s.io/v1alpha3",
                      "kind": "VSphereMachineTemplate",
                      "name": args.name
                  },
                  "version": "v1.18.2"
              }
          }
      }
  }

  obj = namedtuple('MachineDeployment', 'group plural body name')
  kind = obj(group='cluster.x-k8s.io',
             plural='machinedeployments', body=yaml, name=name)

  k8s_config = config.load_kube_config()
  k8s_client = client.api_client.ApiClient(configuration=k8s_config)
  api_instance = kubernetes.client.CoreV1Api(
      kubernetes.client.ApiClient(k8s_config))
  replace_crd(kind)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='commands', dest='subcommand')

    latest = requests.get(
        'https://storage.googleapis.com/kubernetes-release/release/latest.txt').text

    stable = requests.get(
        'https://storage.googleapis.com/kubernetes-release/release/stable.txt').text

    create_parser = subparsers.add_parser(
        'create', help='Create a cluster')
    create_parser.add_argument(
        '-n', action='store', help='Name of the cluster to create', dest="name", type=str, required=True)
    create_parser.add_argument(
        '-vlan', action='store', help='Vlan name used by the cluster', dest="vlan", type=str, required=True, default='VM Network')
    create_parser.add_argument(
        '-vip', action='store', help='Control plane endpoint used by kube-vip', dest="vip", type=str, required=True)
    create_parser.add_argument(
        '-w', action='store', help='Number of workers', dest="workers", type=int, default=3, required=False)
    create_parser.add_argument(
        '-m', action='store', help='Number of master', dest="masters", type=int, default=1, required=False)
    create_parser.add_argument(
        '-c', action='store', help='Number of cpu', dest="cpu", type=int, default=4)
    create_parser.add_argument(
        '-r', action='store', help='Amount of ram', dest="ram", type=int, default=8192)
    create_parser.add_argument(
        '-d', action='store', help='Size of hard disk', dest="hd", type=int, default=50)
    create_parser.add_argument(
        '-e', action='store', help='Environment you want to deploy', dest="env", type=str, default='lab', required=False)
    create_parser.add_argument(
        '-v', action='store', help='Kube-apiserver release', dest="release", type=str, default='v1.18.2', required=False)
    create_parser.add_argument(
        '-t', action='store', help='Template to use', dest="template", type=str, default='ubuntu-1804-kube-v1.18.2', required=False)
    create_parser.add_argument(
        '-f', action='store', help='Folder to use', dest="vmfolder", type=str, default='vm', required=False)
    create_parser.add_argument(
        '-s', action='store', help='vCenter to use', dest="server", type=str, default='192.168.1.60', required=True)
    create_parser.add_argument(
        '-dc', action='store', help='vsphere Datacenter to use', dest="dc", type=str, default='LabDC', required=True)
    create_parser.add_argument(
        '-u', action='store', help='vSphere username to use', dest="username", type=str, required=True)
    create_parser.add_argument(
        '-p', help='vSphere password to use', dest="password", type=str, required=False)
    create_parser.add_argument(
        '-ds', help='datstore to use', dest="datastore", type=str, required=True)


    delete_parser = subparsers.add_parser(
        'delete', help='Delete a cluster')
    delete_parser.add_argument(
        '-n', action='store', help='Name of the cluster to create', dest="name", type=str, required=True)
    delete_parser.add_argument(
        '-e', action='store', help='Environment', dest="env", type=str, default='lab', choices=['lab'], required=True)

    list_parser = subparsers.add_parser(
        'list', help='list all clusters deployed')

    scale_parser = subparsers.add_parser(
        'scale', help='Scale a cluster')
    scale_parser.add_argument(
        '-n', action='store', help='Name of the cluster to scale', dest="name", type=str, required=True)
    scale_parser.add_argument(
        '-w', action='store', help='Number of workers to scale', dest="workers", type=int, required=False)

    upgrade_parser = subparsers.add_parser(
        'upgrade', help='upgrade a cluster (control/data plane)')
    upgrade_parser.add_argument(
        '-n', action='store', help='Name of the cluster to upgrade', dest="name", type=str, required=True)
    upgrade_parser.add_argument(
        '-t', action='store', help='Template to do the upgrade', dest="template", type=str, required=True)
    upgrade_parser.add_argument(
        '-U', action='store', help='release to upgrade. e.g. -U v1.18.2', dest="upgrade", type=str, required=True)
    upgrade_parser.add_argument(
        '-f', action='store', help='Folder of template to use', dest="vmfolder", type=str, default='vm', required=False)
    upgrade_parser.add_argument(
        '-vlan', action='store', help='Vlan name used by the cluster', dest="vlan", type=str, required=True, default='VM Network')
    upgrade_parser.add_argument(
        '-s', action='store', help='vCenter to use', dest="server", type=str, default='192.168.1.60', required=True)
    upgrade_parser.add_argument(
        '-ds', action='store', help='vCenter to use', dest="datastore", type=str, required=True)
    upgrade_parser.add_argument(
        '-dc', action='store', help='vCenter to use', dest="dc", type=str, required=True)

    kubeconfig_parser = subparsers.add_parser(
        'kubeconfig', help='get kubeconfig for specified cluster')
    kubeconfig_parser.add_argument(
        '-n', action='store', help='Name of the cluster you want to retrieve kubeconfig', dest="name", type=str, required=True)

    args = parser.parse_args()

    if len(sys.argv) <= 1:
        print('Usage: main.py -h')
        sys.exit()

    if args.subcommand == 'list':
        clusters = list_clusters()
        print('Clusters deployed: \n')
        for cluster in clusters:
            print(cluster)

    if args.subcommand == 'delete':
        delete_cluster(args)

    if args.subcommand == 'create':
        if not args.password:
            args.password = getpass.getpass(
                prompt='Enter password for host %s and user %s: ' %
                       (args.server, args.username))
            create_cluster(args)
        else:
            create_cluster(args)

    if args.subcommand == 'scale':
        scale_cluster(args)

    if args.subcommand == 'upgrade':
        upgrade_cluster(args)

    if args.subcommand == 'kubeconfig':
        get_kubeconfig(args)

