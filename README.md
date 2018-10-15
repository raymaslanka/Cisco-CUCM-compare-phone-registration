# Cisco CUCM - compare phone registration states by querying RISDB
This demonstrates how to find the registered phones to various servers in a CUCM cluster, write that to a SQL database, and then at a later time find phones no longer registered or registered to different CUCM servers.

The example utilizes Python 3.6.2 and the required libraries will be noted.

The intention was to use this as a fast tool to find "missing" phones after CUCM cluster reboots or upgrades.  This is possible from Cisco RTMT but can be cumbersome and the output sometimes limited or confusing.   

Since CUCM still limits the number of records returned, I don't think I'll develop this much further and will continue to work with RTMT.  If you are looking for next steps, prompting or controlling for different AXL versions would be helpful.

See https://developer.cisco.com/site/axl/
