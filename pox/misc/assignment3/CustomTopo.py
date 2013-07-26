'''
Coursera:
- Software Defined Networking (SDN) course
-- Module 3 Programming Assignment

Professor: Nick Feamster
Teaching Assistant: Muhammad Shahbaz
'''
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import irange,dumpNodeConnections
from mininet.log import setLogLevel

count1 = 1
count2 = 1
count3 = 1

class CustomTopo(Topo):
    "Simple Data Center Topology"
    "linkopts - (1:core, 2:aggregation, 3: edge) parameters"
    "fanout - number of child switch per parent switch"
    def __init__(self, linkopts1, linkopts2, linkopts3, fanout=2, **opts):
        # Initialize topology and default options
        Topo.__init__(self, **opts)
        self.fanout = fanout
          
        # Add your logic here ...
	coreSwitch = self.addSwitch('c1')
	
        for i in irange(1,self.fanout):
            global count1, count2, count3
            aggregationSwitch = self.addSwitch('a%s' % count1)
            self.addLink( coreSwitch, aggregationSwitch, **linkopts1)
            count1 = count1 + 1 
            
            for j in irange(1,self.fanout):
                global count1, count2 
                edgeSwitch = self.addSwitch('e%s' % count2)
                self.addLink( edgeSwitch, aggregationSwitch, **linkopts2)
                count2 = count2 + 1
                
                for k in irange(1, self.fanout):
                    global count3
                    host = self.addHost('h%s' % count3)
                    self.addLink( host, edgeSwitch, **linkopts3)
                    count3 = count3 + 1
                
               

topos = { 'custom': ( lambda: CustomTopo() ) }
