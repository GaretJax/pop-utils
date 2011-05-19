// -------------------------------------------------------------
// Parallel Matrix multiplication by blocks
// Authors: Pierre Kuonen
// Creation: 11.12.2009
// Modifications: March 2011, for Labo 2b course UniFR 2011
// -------------------------------------------------------------

#include <stdio.h>
#include <timer.h>
#include "common/Matrix2Dlc.h"
#include "common/Matrix2Dcl.h"
#include "MatWorker.ph"

#include <iostream>
#include <fstream>
#include <string>

#define nbMaxMachines 200
#define MachinesList "machines.ip"

// -------------------------------------------------------------
// Read  the file 'fileName' containing the list of machines
// and fill the array 'machines' and returns the number of machines
int getAvailableMachines(char* fileName, POPString* machine[])
{
  int nbOfMachines = 0;
  FILE* f;
  if ( (f = fopen(fileName, "r"))!=NULL)
  {
    char* s;
    while (!feof(f))
    {
      s=(char*)malloc(100);
      fscanf(f, "%s", s);
      if (strlen(s)>0)
      {
        machine[nbOfMachines] = new POPString(s);
	      nbOfMachines++;
      }
    }
    fclose(f);
  } else
  {
    nbOfMachines=1;
    machine[0] = new POPString("localhost"); 
  }
  return nbOfMachines;
}

//------------------------------
int main(int argc, char** argv)
{
  if (argc<4)
  {//  parocrun objmap ./main argv[0] argv[1] argv[2] argv[3] argv[4]
    printf("Usage: parocrun objmap ./%s size divLine divCol resultFileName\n\n",
            argv[0]);
    return 0;
  }
  
  int Alines ;          //argv[1];
  int Acols;            //argv[1];
  int Bcols;            //argv[1];
  int divLine;          //argv[2];
  int divCol;           //argv[3];
  char* resultFileName; //argv[4];

  
// Get the execution parameters
  Alines   = Acols = Bcols = atoi(argv[1]);
  divLine  = atoi(argv[2]);
  divCol   = atoi(argv[3]);
 
  // Check parameters consistency
 if (argc>4) resultFileName=argv[4]; else resultFileName=NULL; 
  
 if ((Alines % divLine) != 0)
  {	  
    printf("Size of the Matrix must a muliple of divLine\n\n");
    return 0;
  }  

 if ((Alines % divCol) != 0)
  {	  
    printf("Size of the Matrix must a muliple of divCol\n\n");
    return 0;
  }  

  int nbWorker = divLine*divCol;


 // Get the available machines
  POPString* machine[nbMaxMachines];  
  int nbOfMachines = getAvailableMachines(MachinesList, machine);
  
  printf("Available machines:\n");
  for (int i=0; i<nbOfMachines; i++)

    printf("  %d = %s \n", i, (const char*)(*machine[i])); 

  printf("\nsize=%d, divLine=%d, divCol=%d, Workers=%d  \n\n",
                            Alines, divLine, divCol, nbWorker);


 // Matrix A and B declaration and initialisation
  Matrix2Dlc a(Alines,Acols);
  Matrix2Dcl b(Acols,Bcols);
  
  // Randomly initialize Matrix a and b 
  a.init();  
  b.init();

  //Workers declaration
  MatWorker* mw[divLine][divCol];

  Timer timer;
  double initTime, totalTime, sendTime;

  timer.Start(); //----------------------------------------- Start Timer
  
  try
  {
    //Workers creation
    srand(time(NULL));
    int shift = rand() % nbOfMachines;
    for (int i=0; i<divLine; i++)
      for (int j=0; j<divCol; j++)
        mw[i][j] = new MatWorker(j+i*divCol, Alines/divLine, Acols, Bcols/divCol, *(machine[(j+i*divCol+shift)%nbOfMachines]));

    // Get time to create all workers
    initTime = timer.Elapsed();  // ---------------------- Initialisation Time
  
    //Send the bloc of Matrix A and the Matrix B
    for (int i=0; i<divLine; i++)
      for (int j=0; j<divCol; j++)
        mw[i][j]->solve(a.getLinesBloc(i*Alines/divLine, Alines/divLine), b.getColsBloc(j*Bcols/divCol, Bcols/divCol));
     
    // Get time to send all data to workers
    sendTime = timer.Elapsed() - initTime;  // ------------ Sending Time
    printf("\nStart computation...\n");

    //Create matrix for getting the results
    Matrix2Dlc res(Alines/divLine,Bcols/divCol);

    //Vector to store wait time of workers
    double workerTw[divLine][divCol];
    //Vector to store computing time of workers
    double workerTc[divLine][divCol];

    //Get the result and put inside matrix A    
    for (int i=0; i<divLine; i++)
      for (int j=0; j<divCol; j++)
      {
        res=mw[i][j]->getResult(workerTw[i][j], workerTc[i][j]);
        a.setBloc(i*Alines/divLine, j*Acols/divCol, res);
      }

    // Get the elapsed time since all data have been sent
    totalTime = timer.Elapsed() - sendTime - initTime;  // --- Computing Time
    timer.Stop();
  
    printf("...End of computation\n"); 
    printf("\nTime (init, send and computing) = %g %g %g sec\n\n",
            initTime, sendTime, totalTime);

    // Storage of Results and Parametres on the file resultFileName
    if (resultFileName!=NULL)
    {
      FILE* f = fopen(resultFileName, "a");
      if (f!=NULL)
      {
        fprintf(f, "%d\t%d\t%d\t%g\t%g\t%g",
                Alines, divLine, divCol, initTime, sendTime, totalTime); 
        for (int i=0; i<divLine; i++)
          for (int j=0; j<divCol; j++)
            fprintf(f, "\t%g\t%g", workerTw[i][j],workerTc[i][j]);
        fprintf(f,"\n");
        fclose(f);
      } else
        printf("\nERROR OPENING result file - no results has been saved !!\n"); 
    }

    // Delete the workers
    for (int i=0; i<divLine; i++)
      for (int j=0; j<divCol; j++)
        if (mw[i][j]!=NULL) delete mw[i][j];
  } // end try

  catch (POPException *e)
  {
    printf("Object creation failure\n");
    return 0;
  }
  return 0;
}
