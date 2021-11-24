#
# *** Assigment 1
#

VAGRANTFILE_API_VERSION = "2"
# set docker as the default provider
ENV['VAGRANT_DEFAULT_PROVIDER'] = 'docker'
# disable parallellism so that the containers come up in order
ENV['VAGRANT_NO_PARALLEL'] = "1"
ENV['FORWARD_DOCKER_PORTS'] = "1"
# minor hack enabling to run the image and configuration trigger just once
ENV['VAGRANT_EXPERIMENTAL'] = "typed_triggers"

unless Vagrant.has_plugin?("vagrant-docker-compose")
  system("vagrant plugin install vagrant-docker-compose")
  puts "Dependencies installed, please try the command again."
  exit
end

# Name of Docker images built:
NODE_IMAGE = "ds/assigment-01/node:1.1"

# Node definitions
NODES  = { :nameprefix => "node-",  # nodes names: node-1, node-2, etc.
              :subnet => "10.0.1.",
              :ip_offset => 100,  # node IP addresses: 10.0.1.101, .102, .103, etc
              :image => NODE_IMAGE,
        }
# Number of nodes to start:
NODES_COUNT = 4

# Common configuration
Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  # Before the 'vagrant up' command is started, build docker images:
  config.trigger.before :up, type: :command do |trigger|
    trigger.name = "Build docker image"
    trigger.ruby do |env, machine|
      puts "Building node image."
      `docker build . -t "#{NODE_IMAGE}"`
    end
  end

  config.vm.synced_folder ".", "/vagrant", type: "rsync", rsync__exclude: ".*/"
  config.ssh.insert_key = false

  # Definition of N nodes
  (1..NODES_COUNT).each do |i|
    node_ip_addr = "#{NODES[:subnet]}#{NODES[:ip_offset] + i}"
    node_name = "#{NODES[:nameprefix]}#{i}"
    # Definition of node
    config.vm.define node_name do |s|
      s.vm.network "private_network", ip: node_ip_addr
      s.vm.hostname = node_name
      s.vm.provider "docker" do |d|
        d.image = NODES[:image]
        d.name = node_name
        d.has_ssh = true
      end
      s.vm.post_up_message = "Node #{node_name} up and running. You can access the node with 'vagrant ssh #{node_name}'}"
    end
  end

end

# EOF
