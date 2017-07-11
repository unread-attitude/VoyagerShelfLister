#!/m1/shared/bin/perl

# 2012 modified by Michael Doran

#(c)#====================================================================
#(c)#
#(c)#      Copyright 2007-2009 Ex Libris (USA) Inc.
#(c)#                      All Rights Reserved
#(c)#
#(c)#====================================================================

# Allows on-the-fly display of files in the voyager /rpt directory

#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; either version 2
#of the License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

#------------------------------------------------------------------
# PROGRAM: HTTP/CGI Report Files Front End Display
# AUTHOR:  Debra Venckus, debra.venckus@endinfosys.com
# LANGUAGE: PERL, version 4.0 and higher
# DESCRIPTION:  Read in the contents of the /rpt directory that are
# relevant to acq, cat, and circ batch jobs and display
#------------------------------------------------------------------
#
require "cgi-lib.pl";
require "config.pl";

$DeBuGcOnFiG = 0;

LoadConfig();
CheckProcess();

# The following function call is necessary to establish that the output of
# this program will be html.  Web browsers look for this information, and
# if it is not there, then the browser will display nothing.

PrintHTMLHeader();


print "<HTML>\n";
print "<HEAD>\n";
print   "<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; " .
                "charset=iso-8859-1\">\n";
print   "<META NAME=\"Author\" CONTENT=\"Debra Venckus\">\n";
print   "<META NAME=\"Author\" CONTENT=\"Michael Doran\">\n";
print   "<TITLE>Voyager Report Files</TITLE>\n";
print "</HEAD>\n";
print "<BODY>\n";
print "<CENTER><H1><I>ShelfLister &quot;Marked Items&quot; Files</I></H1></CENTER><BR>";
print "<A HREF=\"../\"> Return to Main Page </A><BR>\n";
print "<P><HR WIDTH=\"100%\"><BR>\n";

opendir(RPTDIR, "$voydir/$site/webadmin/shelflister") or
        die("Couldn't open $voydir/$site/webadmin/shelflister: $!");
@files = sort grep(!/^\./, readdir(RPTDIR));

print qq(
  <b>To download a file</b>
  <ul>
    <li>
      Right click and select &quot;Save Target (or Link) As...&quot; 
    </li>
    <li>
      Save the file in desired directory
    </li>
    <li>
      Once the file is saved, open it in <b>WordPad</b> and re-save
    </li>
    <li>
      Tutorial: <a href="http://rocky.uta.edu/doran/shelflister/ShelfLister20markeditems.pdf">import the file into MS Access</a> 
    </li>
  </ul>
);

foreach $filename (@files)
{
    print "<A HREF=\"../shelflister/$filename\"> " .
          "$filename </A><BR>\n";
}
closedir(RPTDIR);

print "<HR WIDTH=\"100%\"><P></BODY></HTML>\n";








