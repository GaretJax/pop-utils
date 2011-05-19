#ifndef _MATWORKER_PH
#define _MATWORKER_PH

#include <timer.h>
#include "common/Matrix2Dlc.h"
#include "common/Matrix2Dcl.h"

parclass MatWorker
{
  classuid(1500);

  public:
    MatWorker();
    MatWorker(int i, int nbLineA, int nbColA, int nbColB, POPString machine) @{od.url(machine);};
    ~MatWorker();
    
    async conc void solve(Matrix2Dlc a, Matrix2Dcl b);    
    sync mutex Matrix2Dlc getResult(double &tw, double &tc);
    
  private:
    Matrix2Dlc* c;
    int nbLinesA, nbColsA, nbColsB;
    int id;

    Timer timer;
    double computeTime, waitTime;
};
#endif

