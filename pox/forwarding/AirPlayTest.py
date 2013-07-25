# This component is momdified version of l2_learning
# It is modified according to the requirement of the AirPlayProject

# from COMPONENT import FNCTION/OBJECT/METHOD
from pox.core import core
from pox.lib.util import str_to_dpid, dpid_to_str, str_to_bool

import pox.openflow.libopenflow_01 as of
import pox.lib.packet as packet
import time

log = core.getLogger()

# We don't want to flood immediately when a switch connects.
# Can be overriden on commandline.
_flood_delay = 0

#############################################################################################
#############################################################################################
# Global learning table & pairdb table for AirPlay project
table = set([])
mac_list = ["98:D6:BB:2B:57:F2","00:16:CB:8A:A8:7E"]

class GlobeLearningTable(object):
  
  def __init__(self, src_mac,dst_mac ,port, dpid):
    self.src_mac = src_mac
    self.dst_mac = dst_mac
    self.port = port
    self.dpid = dpid
  
  def __hash__(self):
        return hash((self.src_mac,self.dst_mac,self.port, self.dpid))

  def __eq__(self, other):
        if not isinstance(other, type(self)): return NotImplemented
        return self.src_mac == other.src_mac and self.dst_mac == other.dst_mac and self.port == other.port and self.dpid == other.dpid

  def add(self):
    global table
    if self not in table:
      table.add(self)
#############################################################################################
#############################################################################################

class LearningSwitch (object):
  """
  The learning switch "brain" associated with a single OpenFlow switch.

  When we see a packet, we'd like to output it on a port which will
  eventually lead to the destination.  To accomplish this, we build a
  table that maps addresses to ports.

  We populate the table by observing traffic.  When we see a packet
  from some source coming from some port, we know that source is out
  that port.

  When we want to forward traffic, we look up the desintation in our
  table.  If we don't know the port, we simply send the message out
  all ports except the one it came in on.  (In the presence of loops,
  this is bad!).

  In short, our algorithm looks like this:

  For each packet from the switch:
  1) Use source address and switch port to update address/port table
  2) Is transparent = False and either Ethertype is LLDP or the packet's
     destination address is a Bridge Filtered address?
     Yes:
        2a) Drop packet -- don't forward link-local traffic (LLDP, 802.1x)
            DONE
  3) Is destination multicast?
     Yes:
        3a) Flood the packet
            DONE
  4) Port for destination address in our address/port table?
     No:
        4a) Flood the packet
            DONE
  5) Is output port the same as input port?
     Yes:
        5a) Drop packet and similar ones for a while
  6) Install flow table entry in the switch so that this
     flow goes out the appopriate port
     6a) Send the packet out appropriate port
  """
  
  def __init__ (self, connection,transparent):
    # Switch we'll be adding L2 learning switch capabilities to
    self.connection = connection
    self.transparent = transparent
    

    # Our table
    self.macToPort = {}

    # We want to hear PacketIn messages, so we listen
    # to the connection
    connection.addListeners(self)

    # We just use this to know when to log a helpful message
    self.hold_down_expired = _flood_delay == 0

    log.debug("Initializing LearningSwitch, transparent=%s",
              str(self.transparent))

  def _handle_PacketIn (self, event):
    """
    Handle packet in messages from the switch to implement above algorithm.
    """
    
    def flood (message = None):
      """ Floods the packet """
      msg = of.ofp_packet_out()
      if time.time() - self.connection.connect_time >= _flood_delay:
        # Only flood if we've been connected for a little while...

        if self.hold_down_expired is False:
          # Oh yes it is!
          self.hold_down_expired = True
          log.info("%s: Flood hold-down expired -- flooding",
              dpid_to_str(event.dpid))

        if message is not None: log.debug(message)
        # log.debug("%i: flood %s -> %s", event.dpid,packet.src,packet.dst)
        # OFPP_FLOOD is optional; on some switches you may need to change
        # this to OFPP_ALL.
        msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
      else:
        pass
        #log.info("Holding down flood for %s", dpid_to_str(event.dpid))
      msg.data = event.ofp
      msg.in_port = event.port
      self.connection.send(msg)

    def drop (duration = None):
      """
      Drops this packet and optionally installs a flow to continue
      dropping similar ones for a while
      """
      if duration is not None:
        if not isinstance(duration, tuple):
          duration = (duration,duration)
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.idle_timeout = duration[0]
        msg.hard_timeout = duration[1]
        msg.buffer_id = event.ofp.buffer_id
        self.connection.send(msg)
      elif event.ofp.buffer_id is not None:
        msg = of.ofp_packet_out()
        msg.buffer_id = event.ofp.buffer_id
        msg.in_port = event.port
        self.connection.send(msg)
    packet = event.parsed
    
    if not self.transparent: # 2
      if packet.type == packet.LLDP_TYPE or packet.dst.isBridgeFiltered():
        drop() # 2a
        return
        
    # Mac address of device is converted into uppercase string    
    # creating l2 table for individual switch & global learning table 
    self.macToPort[packet.src] = event.port # 1
    
    ##################################################################################################################################
    ##################################################################################################################################
    # Constants for AirPlayProject
    dpid = event.dpid
    
    packet_src = str(packet.src)
    packet_src_mac = packet_src.upper()
    
    packet_dst = str(packet.dst)
    packet_dst_mac = packet_dst.upper()
    log.debug("\n###########################\n   DEBUGGING BEGINS HERE   \n###########################\n")
   
    entry = GlobeLearningTable(packet_src_mac, packet_dst_mac, event.port, dpid)
    entry.add()
    log.debug ("\n packet_src_mac = %s \n packet_dst_mac = %s \n Elements inside a table = %s \n", packet_src_mac, packet_dst_mac, len(table)) 
    
    # Algorithm for Air_Play
    # 1) Is packet a multicast packet ?
      # 2) Is packet an IPv4 packet ?
        # 3) Is packet a multicast DNS packet ?
           # 4) Iterate over pairdb table for client_mac, host_mac:
              # 5) if packet.src == client_mac or dst_mac == packet.src :
                 # 6) Iterate over global table and send packet to apt. switch using its DPID
                    # 7) If src_mac of the device is in global table send packet to switch to whom device is connected using its DPID 


      
    if packet.dst.isMulticast(): # 1)
      log.debug("\n 1) Found Multicast Packet \n")
      
      ip_packet = packet.find('ipv4')
      if ip_packet is not None:  # 2)
        ip_packet = packet.payload
        src_ip = ip_packet.srcip
        dst_ip = ip_packet.dstip
        log.debug("\n 2) Found multicast IPv4 \n src_ip = %s\n dst_ip = %s \n",str(src_ip),str(dst_ip))

        if dst_ip == "224.0.0.251" or dst_ip == "224.0.0.252": # 3)
          log.debug("\n 3)Found multicast DNS Packet because of dst_ip \n")
       
          for mac in mac_list: # 4)
            #log.debug("\n 4) From mac_list \n mac = %s \n From packet_in \n packet_src_mac = %s \n",str(mac),packet_src_mac)
                  
            if mac == packet_src_mac: # 5)
              log.debug("\n 5) The following packet_src_mac is in mac_list = %s \n",str(packet_src_mac))
              
              for obj in table : # 6)
                log.debug("\n 7) Input switch_DPID = %s \n    Output switch_DPID = %s \n",dpid_to_str(event.dpid),dpid_to_str(obj.dpid))
                log.debug("\n Input switch_physical port = %ld \n Output switch_physical port = %ld \n",event.port,obj.port)
                po = of.ofp_packet_out(data = event.data, action = of.ofp_action_output(port = obj.port))
                core.openflow.sendToDPID(obj.dpid,po)

                # log.debug("\n 6) Level 6 in the algorithm \n")
                # if obj.src_mac == mac : # 7)
                # log.debug("\n 7) Finally in the last branch \n")
                      
    ###############################################################################################################################################################
    ###############################################################################################################################################################

    else:
      if packet.dst not in self.macToPort: # 4
        log.debug("Port for %s unknown -- flooding" % (packet.dst,)) 
        flood() # 4a
      else:
        port = self.macToPort[packet.dst]
        if port == event.port: # 5
          # 5a
          log.warning("Same port for packet from %s -> %s on %s.%s.  Drop."
              % (packet.src, packet.dst, dpid_to_str(event.dpid), port))
          drop(10)
          return
        # 6
        log.debug("installing flow for %s.%i -> %s.%i" %
                  (packet.src, event.port, packet.dst, port))
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet, event.port)
        msg.idle_timeout = 10
        msg.hard_timeout = 30
        msg.actions.append(of.ofp_action_output(port = port))
        msg.data = event.ofp # 6a
        self.connection.send(msg)
    
  

class l2_learning (object):
  """
  Waits for OpenFlow switches to connect and makes them learning switches.
  """
  def __init__ (self, transparent):
    core.openflow.addListeners(self)
    self.transparent = transparent

  def _handle_ConnectionUp (self, event):
    log.debug("Connection %s" % (event.connection,))
    log.debug("\nSwiitch %s has come up.\n",dpid_to_str(event.dpid))
    LearningSwitch(event.connection, self.transparent)


def launch (transparent=False, hold_down=_flood_delay):
  """
  Starts an L2 learning switch.
  """
  try:
    global _flood_delay
    _flood_delay = int(str(hold_down), 10)
    assert _flood_delay >= 0
  except:
    raise RuntimeError("Expected hold-down to be a number")

  # page no 12-13 of pox wiki explains core.registerNew()---> Registering Components
  core.registerNew(l2_learning, str_to_bool(transparent))
