#include "MatWorker.ph"
#include <stdio.h>
#include <timer.h>
#include <iostream>
#include <fstream>
#include <string>

MatWorker::MatWorker()
{
   nbLinesA = 0;
   nbColsA = 0;
   nbColsB = 0;
   c = NULL;
}

MatWorker::MatWorker(int i, int nbLineA, int nbColA, int nbColB, paroc_string machine)
{
   nbLinesA = nbLineA;
   nbColsA = nbColA;
   nbColsB = nbColB;
   c = new Matrix2Dlc(nbLineA,nbColB);
   c->zero();

   //printf("Worker %d created on machine:%s\n",i, (const char*)paroc_system::GetHost());
  timer.Start();
}

MatWorker::~MatWorker()
{
   if (c != NULL) delete c;
}

void MatWorker::solve(Matrix2Dlc a, Matrix2Dcl b)
{
  waitTime = timer.Elapsed();


  for (int j=0; j<nbLinesA; j++)
    for (int k=0; k<nbColsB; k++)  // c->set(j,k, a.get(j,k) + b.get(j,k)); 
      for (int l=0; l<nbColsA; l++)
        c->set(j,k,c->get(j,k)+a.get(j,l) * b.get(l,k));
   computeTime=timer.Elapsed() - waitTime; timer.Stop();
}


Matrix2Dlc MatWorker::getResult(double &tw, double &tc)
{
   tw = waitTime;
   tc = computeTime;
   return *c;
}

@pack(MatWorker);
