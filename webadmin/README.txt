# 2012-04-30 Michael Doran

Instructions for making your ShelfLister "marked items" files 
available via the Voyager WebAdmin utility.  In the paths below, 
replace {xxxdb} with your db name and {sl-dist-path} with your 
ShelfLister distribution path.

As the "voyager" user:

1) Make a copy of your current WebAdmin index.html file:

   cd /m1/voyager/{xxxdb}/webadmin/
   cp -p index.html index.html.orig

   and then replace the current WebAdmin index.html file 
   with the index.html file included in this directory:

   cp -p /{sl-dist-path}/webadmin/index.html index.html

2) Move the shelflisterfiles.cgi script to the webadmin
   cgi-bin directory and give it executable permissions: 

   cd /m1/voyager/{xxxdb}/webadmin/cgi-bin/
   cp /{sl-dist-path}/webadmin/shelflisterfiles.cgi . 
   chmod 755 shelflisterfiles.cgi

3) Create a 'shelflister' directory under webadmin and give
   it world-writeable permissions:

   cd /m1/voyager/{xxxdb}/webadmin/
   mkdir shelflister
   chmod 777 shelflister

4) In the shelfister3.ini configuration file, specify 
   /m1/voyager/{xxxdb}/webadmin/shelflister as the
    marked item file.
