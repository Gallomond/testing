# -*- mode: ruby -*-
# vi: set ft=ruby :

$INSTALL_BASE = <<SCRIPT
  sudo apt-get update
  sudo apt-get install -y build-essential vim emacs git python3
  sudo apt-get update
  sudo apt-get install -y build-essential vim emacs

  echo "sudo tc qdisc add dev eth1 root netem loss 10% delay 20ms" > /set-loss.sh
  chmod 755 /set-loss.sh
SCRIPT

Vagrant.configure(2) do |config|
  config.vm.box = "generic/ubuntu1804"
  config.vm.provision "shell", inline: $INSTALL_BASE

  config.vm.synced_folder ".", "/vagrant"
  
  # config.vm.provider "virtualbox" do |vb|
  #   # Display the VirtualBox GUI when booting the machine
  #   vb.gui = true
  #
  #   # Customize the amount of memory on the VM:
  #   vb.memory = "1024"
  # end

  config.vm.define :client, primary: true do |host|
    host.vm.hostname = "client"
    host.vm.network "private_network", ip: "10.0.0.2", netmask: "255.255.255.0",
                    virtualbox__intnet: "class"
  end

  config.vm.define :server do |host|
    host.vm.hostname = "server"
    host.vm.network "private_network", ip: "10.0.0.1", netmask: "255.255.255.0",
                    virtualbox__intnet: "class"
  end
end
