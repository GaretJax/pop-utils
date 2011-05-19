/**
 * File : allocobj.cc
 * Author : Tuan Anh Nguyen
 * Description : Implementation of the batch creation mechanism of parallel objects
 * Creation date : -
 * 
 * Modifications :
 * Authors		Date			Comment
 */


#include "paroc_allocobj.h"
#include "paroc_interface.h"


paroc_mutex paroc_allocobj::lock;

paroc_allocobj::paroc_allocobj(int count)
{
	lock.lock();
	holding=true;
	paroc_interface::batchsize=count;
	paroc_interface::batchindex=0;
}

void paroc_allocobj::release()
{
	if (holding)
	{
		paroc_interface::batchsize=paroc_interface::batchindex=0;
		holding=false;
		lock.unlock();
	}
}

paroc_allocobj::~paroc_allocobj()
{
	release();
}
