#fast:
#	popcc -O1 -O2 -O3  -fforce-addr -fomit-frame-pointer -o MatMul ../Matrix2D.cc ../Matrix2Dlc.cc ../Matrix2Dcl.cc MatWorker.ph MatWorker.cc main.cc
#	parocc -object -O1 -O2 -O3 -fforce-addr -fomit-frame-pointer  -o MatWorker.obj ../Matrix2D.cc ../Matrix2Dlc.cc ../Matrix2Dcl.cc MatWorker.ph MatWorker.cc
#	./MatWorker.obj -listlong > obj.map

application:
	popcc -o MatMul \
	         common/Matrix2D.cc \
	         common/Matrix2Dlc.cc \
	         common/Matrix2Dcl.cc \
	         MatWorker.ph \
	         MatWorker.cc \
	         main.cc

objects:
	popcc -object -o MatWorker.obj\
	                 common/Matrix2D.cc \
	                 common/Matrix2Dlc.cc \
	                 common/Matrix2Dcl.cc \
	                 MatWorker.ph \
	                 MatWorker.cc
	
	./MatWorker.obj -listlong > obj.map

clean:
	rm *.obj *.o
	rm MatMul
	rm common/*.o 

run:
	popcrun obj.map ./MatMul 600 5 2
