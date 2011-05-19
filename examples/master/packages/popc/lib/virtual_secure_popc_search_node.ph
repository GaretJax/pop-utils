/**
 * File : virtual_secure_popc_search_node.ph
 * Author : Clement Valentin (clementval)
 * Description : Parclass header file of the virtual search node (resources discovery)
 * Creation date : 2010/04/19
 * 
 * Modifications :
 * Author		Date 			Description
 * clementval	2010/11/11  Creation of the virtual version of the PSN
 */

#ifndef _VIRT_SECURE_PSN_PH
#define _VIRT_SECURE_PSN_PH

#include "virtual_popc_search_node.ph"

/**
 * @author Valentin Clement
 * The POP-C++ Virtual Search Node (PSN) is in charge of the resources discovery in the GRID when the POP-C++ virtual version is 
 * used. This parallel object is a part of the POP-C++ Global Services.
 */
parclass VirtSecurePOPCSearchNode : public VirtualPOPCSearchNode {

public:
	//Node's constructore 
	VirtSecurePOPCSearchNode(const paroc_string &challenge, bool deamon) @{ od.runLocal(true); od.service(true); };
   
	// Destructor
	~VirtSecurePOPCSearchNode();
   
   //Getter and Setter for the Security Manager reference
   sync seq void setPSMRef(paroc_accesspoint psm);
   sync conc paroc_accesspoint getPSMRef();

   //Getter and Setter for the PKI
   seq sync void setPKI(paroc_string pk);
   conc sync paroc_string getPKI();


   /*
    * Overwritten method
    */

   // Service's entry point to ressource discovery
	conc sync virtual POPCSearchNodeInfos launchDiscovery([in, out] Request req, int timeout);        

	// Node's entry point to propagate request
	seq async virtual void askResourcesDiscovery(Request req, paroc_accesspoint jobmgr_ac, paroc_accesspoint sender, paroc_accesspoint psm);
        
	// Node's return point to give back the response to the initial node
	conc async virtual void callbackResult(Response resp);
   
   //Class Unique Identifier
	classuid(1003);

protected:
   //Reference to the local Security Manager
   paroc_accesspoint _localPSM;  

   //Overwritten methods. Check resources availability
   seq sync bool checkResource(Request req);
};
#endif


   
