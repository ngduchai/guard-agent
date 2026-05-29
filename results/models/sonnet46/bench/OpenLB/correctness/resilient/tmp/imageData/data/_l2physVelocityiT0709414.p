if (strstrt(GPVAL_TERMINALS, 'jpeg') > 0) {set terminal jpeg size 1200,18font ",25"
set output './tmp/imageData/_l2(physVelocity)iT0709414.jpeg'
} else {set terminal png size 1200,18font ",25"
set output './tmp/imageData/_l2(physVelocity)iT0709414.png'
}
set pm3d map
unset key
unset xtics
unset ytics
unset border
set pm3d interpolate 0,0
set lmargin at screen 0
set rmargin at screen 1
set tmargin at screen 0
set bmargin at screen 1
set xlabel "x-axis in m "
set ylabel "y-axis in m "
set cblabel offset 0.5 "l2(physVelocity) in m/s"
set cbrange [0:1.5]
set autoscale fix
set palette defined ( 0 "blue", 1 "green", 2 "yellow", 3 "orange", 4 "red" )
splot './tmp/imageData/data/_l2(physVelocity)iT0709414.matrix' u ($1*0.0005837+-2.22045e-15):($2*0.0005837+-2.22045e-15):3 matrix with pm3d
