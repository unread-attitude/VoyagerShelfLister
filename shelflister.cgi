#!/m1/shared/bin/perl

########################################################################
#
#  ShelfLister  -  development build 90926.13b
#
#  Version: 2.0 release candidate for Unix
#
#  Created by Michael Doran
#    doran@uta.edu
#    817-272-5326
#
#  University of Texas at Arlington Library
#  Box 19497, Arlington, TX 76019, USA
#
########################################################################
#  
#  Copyright 2003-2009, The University of Texas at Arlington ("UTA").
#  All rights reserved.
#
#  By using this software the USER indicates that he or she 
#  has read, understood and and will comply with the following:
#
#  UTA hereby grants USER permission to use, copy, modify, and
#  distribute this software and its documentation for any 
#  purpose and without fee, provided that:
#
#  1. the above copyright notice appears in all copies of the
#  software and its documentation, or portions thereof, and
#
#  2. a full copy of this notice is included with the software 
#  and its documentation, or portions thereof, and
#
#  3. neither the software nor its documentation, nor portions
#  thereof, is sold for profit.  Any commercial sale or license
#  of this software, copies of the software, its associated
#  documentation and/or modifications of either is strictly
#  prohibited without the prior consent of UTA.
#
#  Title to copyright to this software and its associated
#  documentation shall at all times remain with UTA.  No right
#  is granted to use in advertising, publicity or otherwise any
#  trademark, service mark, or the name of UTA.
#
#  This software and any associated documentation are provided
#  "as is," and UTA MAKES NO REPRESENTATIONS OR WARRANTIES,
#  EXPRESSED OR IMPLIED, INCLUDING THOSE OF MERCHANTABILITY OR
#  FITNESS FOR A PARTICULAR PURPOSE, OR THAT USE OF THE SOFTWARE,
#  MODIFICATIONS, OR ASSOCIATED DOCUMENTATION WILL NOT INFRINGE
#  ANY PATENTS, COPYRIGHTS, TRADEMARKS OR OTHER INTELLECTUAL
#  PROPERTY RIGHTS OF A THIRD PARTY. UTA, The University of Texas
#  System, its Regents, officers, and employees shall not be
#  liable under any circumstances for any direct, indirect, special,
#  incidental, or consequential damages with respect to any claim
#  by USER or any third party on account of or arising from the
#  use, or inability to use, this software or its associated
#  documentation, even if UTA has been advised of the possibility
#  of those damages.
#
#  Submit commercialization requests to: The University of Texas
#  at Arlington, Office of Grant and Contract Services, 701 South
#  Nedderman Drive, Box 19145, Arlington, Texas 76019-0145,
#  ATTN: Director of Technology Transfer.
#
########################################################################

# 2009-07-01  Removed mouse-over toggle but left the omoo code in place

#  Best practices.  ;-)

use strict;

unless (eval "use Encode") {
    ErrorConfig("fatal", "Missing Perl module", "$@") if $@;
}

unless (eval "use File::Basename") {
    ErrorConfig("fatal", "Missing Perl module", "$@") if $@; 
}

#  This script uses the Perl DBI and DBD::Oracle modules

unless (eval "use DBI") {
    ErrorConfig("fatal", "Missing Perl module", "$@") if $@;
}

eval("use DBD::Oracle");
ErrorConfig("fatal", "Missing Perl module", "$@") if $@;

use Fcntl qw(:flock);

use File::Copy "cp";

# Relative path to directories for putting the configuration files:
#  -- shelflister.ini
#  -- shelflister.English
use lib '../../newbooks';
use lib '../../shelflister';

# Read in base configuration file
#require "shelflister.ini";
unless (eval qq(require "shelflister.ini")) {
    ErrorConfig("fatal", "Couldn't load required config file", "$@");
} 

# Voyager SID
$ENV{ORACLE_SID} = "$ShelfListerIni::oracle_sid";

#  Parameters needed to connect to the Voyager database
#
#  New for this version of ShelfLister is the ability to
#  connect to the Voyager database from any Unix server
#  that has an Oracle client and the Perl DBI/DBD::Oracle
#  modules installed.

# ORACLE_HOME
$ENV{ORACLE_HOME}  = "$ShelfListerIni::oracle_home";

# Voyager database name
my $db_name = "$ShelfListerIni::db_name";

# Image directory 
my $image_dir = "$ShelfListerIni::image_dir";

#  Use the Oracle read-only login that works with the
#  Voyager canned reports Access database.
my $username = "$ShelfListerIni::oracle_username";
my $password = "$ShelfListerIni::oracle_password";

# T => true, F => false
my $debug = "F";
my $valid = "F";
my $error_out_count = 0;

my ($dbh,$sth);

#  This value is relative to the Apache webserver document root,
#  and shouldn't need to be edited.

my $this_script  = "$ENV{SCRIPT_NAME}"; 

my $report_dir   = "$ShelfListerIni::output_directory";

#  ShelfLister is designed so that you can setup multiple
#  instances for different projects.  This is usually done
#  by copying the shelflister.cgi script and giving it a
#  different name.  The "marked items" file will be given
#  the same name, but with a ".txt" file extension.

my $out_file     = fileparse("$this_script", qr/\.[^.]*/) . ".txt";

#  Another alternative is just to hardcode the output filename
#my $out_file     = "shelflister.inp";

#  Application name and version number

my $this_app      = "ShelfLister";
#my $this_app_link = qq(<a href="$this_script?show=s1\&$ENV{'QUERY_STRING'}">$this_app</a>);
my $this_app_link = qq(<a href="$this_script">$this_app</a>);
my $version       = "2.0 Unix";


######################################
#  This allows (or disallows) the ability to update and delete
#  entries in the marked item flat file.  The options are "yes"
#  or "no".  In the current state of development this should
#  *NOT* be turned on.  Leave as "no".  (This feature can result
#  in data loss in the marked items flat file due to problems in
#  file locking.) 

my $update_ok = "no";


########################################################################
#                                                                      #
#    * * * * * * * *                               * * * * * * * *     #
#    * * * * * * * *       Stop editing here!      * * * * * * * *     #
#    * * * * * * * *                               * * * * * * * *     #
#                                                                      #
########################################################################
#
#  Most Voyager sites should not have to edit code beyond this point.
#
#  However, if you are a Perl programmer or just adventuresome, then
#  by all means have a go.  Commenting is minimal - if you can't  
#  figure out what the code does, then you probably don't want to mess
#  with it.  ;-)
#
########################################################################


#  Parse form data 

my %formdata;

my $doc_type_def = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
            "http://www.w3.org/TR/html4/loose.dtd">';

my @checked_records;

ReadParse();

##########################################################
#  ReadParse
##########################################################
#
#  ReadParse reads in and parses the CGI input.
#  It reads  / QUERY_STRING ("get"  method)
#            \    STDIN     ("post" method)

sub ReadParse {
    my ($meth, $formdata, $pair, $name, $value);

    # Retrieve useful ENVIRONMENT VARIABLES
    $meth = $ENV{'REQUEST_METHOD'};

    # If method unspecified or if method is GET
    if ($meth eq  '' || $meth eq 'GET') {
        # Read in query string
        $formdata = $ENV{'QUERY_STRING'};
    }
    # If method is POST
    elsif ($meth eq 'POST') {
        read(STDIN, $formdata, $ENV{'CONTENT_LENGTH'});
    }
    else {
        die "Unknown request method: $meth\n";
    }

    # name-value pairs are separated and put into a list array
    my @pairs = split(/&/, $formdata);

    foreach $pair (@pairs) {
        # names and values are split apart
        ($name, $value) = split(/=/, $pair);
        # pluses (+'s) are translated into spaces
        $value =~ tr/+/ /;
        # hex values (%xx) are converted to alphanumeric
        $name  =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
        $value =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
        # The code below attempts to ferret out shell meta-characters
        # in the form input.  It replaces them with spaces.
        # looking for the presence of shell meta-characters in $name
        $name  =~ s/[{}\!\$;><&\*'\|]/ /g;
        # looking for the presence of shell meta-characters in $value
        $value =~ s/[{}\!\$;><&\*'\|]/ /g;
        if ($name eq "check") {
            @checked_records = (@checked_records, "$value");
        } else {
            # associative array of names and values created
            $formdata{$name} = $value;
        }
    }
    # De-dup and sort the list of checked records
    if (@checked_records) {
        my @uniq;
        my %seen = ();
        foreach my $i (@checked_records) {
            push (@uniq, $i) unless $seen{$i}++;
        }
        @checked_records = (sort { $a <=> $b } @uniq);
    }
}


##########################################################
#  Assign form data to variables.
##########################################################

# Language of user interface
my $language            = decode_utf8($formdata{'lang'});

LoadLanguageModule($language);

my $back_button = '';

if ($ShelfListerIni::back_button eq "Y") {
    $back_button = qq(<input type="button" value="$Lang::string_back" class="button" onClick="history.go\(-1\);">);
}

my @save_stati;
if (@Lang::save_stati) {
    @save_stati = @Lang::save_stati;
} else {
    @save_stati = @ShelfListerIni::save_stati;
}
 
my $list_display        = '';
$list_display           = decode_utf8($formdata{'mode'});
if (! $list_display) {
    $list_display        = $ShelfListerIni::list_display_default;
}

my $mouse_over          = decode_utf8($formdata{'omoo'});

# Input from Search Form 1 - Barcode entry

my $barcode_start       = decode_utf8($formdata{'bcs'});
my $barcode_end         = decode_utf8($formdata{'bce'});

# Input from Search Form 2 - Call Number entry

my $location_id         = decode_utf8($formdata{'loc_id'});
my $call_num_start      = decode_utf8($formdata{'cns'});
my $call_num_end        = decode_utf8($formdata{'cne'});

# Input from both Search Forms

my $search_type         = decode_utf8($formdata{'search'});
my $show_charge_stats   = decode_utf8($formdata{'charges'});
my $show_browse_stats  	= decode_utf8($formdata{'browses'});
my $show_item_status    = decode_utf8($formdata{'status'});
my $show_callno_plus    = decode_utf8($formdata{'cnplus'});
my $show_boxes          = decode_utf8($formdata{'boxes'});
my $starting_pnt        = decode_utf8($formdata{'stpt'});
$starting_pnt =~ s/\D//g;

# Input from Random Test 
my $random_item_id      = $formdata{'itemid'};

#  Browser detection
#  This part could use some more work.

my $device              = '';
my $browser             = '';
my $user_agent          = $ENV{'HTTP_USER_AGENT'};
my $recs_per_page;
#  Check for type of browser
if ($user_agent =~ /iphone/i) { 
    $recs_per_page       = "50";
    $device              = "iphone";
} elsif ($user_agent =~ /NetFront/i
      || $user_agent =~ /PalmSource/i
   ) {
    $recs_per_page       = "50";
    $device              = "palm";
} else {
    $recs_per_page       = "50";
}

if ($user_agent =~ /Chrome/i) { 
    $browser             = 'chrome';
}

my $ending_pnt          = $starting_pnt + $recs_per_page - 1;

# Input for Item View

my $record_type         = decode_utf8($formdata{'record_type'});
my $record_number       = decode_utf8($formdata{'record_no'});

# Input for misc. views

my $topic               = decode_utf8($formdata{'topic'});
my $show_page           = decode_utf8($formdata{'show'});

# Input for saving to file

my $save_action              = decode_utf8($formdata{'save_action'});
my $save_status              = decode_utf8($formdata{'save_status'});
my $save_bib_id              = decode_utf8($formdata{'save_bib_id'});
my $save_mfhd_id             = decode_utf8($formdata{'save_mfhd_id'});
my $save_item_id             = decode_utf8($formdata{'save_item_id'});
my $save_barcode             = decode_utf8($formdata{'save_barcode'});
my $save_call_no             = decode_utf8($formdata{'save_call_no'});

if      ($show_page eq 's1') {
    PrintSearchForm("s1");
} elsif ($show_page eq 's2') {
    PrintSearchForm("s2");
} elsif ($show_page eq 'mif') {
    ShowMIF();
} elsif ($search_type eq 's1' || $search_type eq 's2') {
    ValidateData();
} elsif ($record_number && $record_type eq 'item') {
    ShowRecordItem();
} elsif ($record_number && $record_type eq 'mfhd') {
    ShowRecordMFHD();
} elsif ($show_page eq 'help') {
    ShowHelp($topic);
} elsif ($show_page eq 'mail') {
    ShowMailSave();
} elsif ($save_status && $save_bib_id) {
    if ($save_action eq "delete") {
        DeleteFromFile();
    } elsif ($save_action eq "update") {
        DeleteFromFile();
        SaveToFile();
    } else {
        SaveToFile();
    }
} elsif ($show_page eq 'random') {
    GenRandomList();
} else {
    $show_page = "s1";
    PrintSearchForm("s1");
    #PrintHomePage();
}

##########################################################
#  LoadLangModule
##########################################################

sub LoadLanguageModule {
    my ($language) = @_;
    if ($language) {
        foreach my $key (keys (%ShelfListerIni::language_modules)) {
            if ($key eq $language) {
                unless (eval qq(require "$ShelfListerIni::language_modules{$key}")) {
                    ErrorConfig("fatal", "Missing Language Module", $@);
                }
                return;
            }
        }
    } else {
        unless (eval qq(require "$ShelfListerIni::language_modules{$ShelfListerIni::default_language}")) {
            ErrorConfig("fatal", "Missing Language Module", $@);
        }
    }
}


##########################################################
#  PrintHomePage 
##########################################################
#
#  Deprecated in v.2.0  
#  Default page is barcode search

sub PrintHomePage {
    PrintHead();
    print encode_utf8(qq(
    <h1>Deprecated</h1>
    ));
    PrintTail();
}


##########################################################
#  PrintSearchForm 
##########################################################
#
#  If the CGI script is called without user input all we 
#  want to do is return the initial HTML search form page.

sub PrintSearchForm {
    my ($form) = @_;
    my $s1_tab = "";
    my $s2_tab = "";
    if ($form eq "s2") {
        $s1_tab     = qq(<li class="off"><a href="$this_script?show=s1">$Lang::string_bc_legend</a></li>);
        $s2_tab     = qq(<li class="on">$Lang::string_callno_legend</li>);
    } else {
        $s1_tab     = qq(<li class="on">$Lang::string_bc_legend</li>);
        $s2_tab     = qq(<li class="off"><a href="$this_script?show=s2">$Lang::string_callno_legend</a></li>);
    }

    ConnectVygrDB();

    # Prepare the first prelimary SQL statement
    my $sth = $dbh->prepare("select location_id, location_name from $db_name.location where suppress_in_opac not in 'Y'") 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;

    my (%location_list);
    while( my ($location_id, $location_name) = $sth->fetchrow_array() ) {
	%location_list  = (%location_list, ($location_name => $location_id));
    }

    DisconnectVygrDB();

    my $hidden_inputs = '';
    if ($list_display) {
        $hidden_inputs .= qq(<input type="hidden" name="mode" value="$list_display">\n);
    }
    if ($mouse_over) {
        $hidden_inputs .= qq(<input type="hidden" name="omoo" value="$mouse_over">\n);
    }
    if ($show_callno_plus) {
        $hidden_inputs .= qq(<input type="hidden" name="cnplus" value="$show_callno_plus">\n);
    }

    PrintHead("$Lang::string_search_h1");

    print qq(
      <h1>$Lang::string_search_h1</h1>

      <div class="tabsContainer">
        <ul class="tabs">
            $s1_tab
            $s2_tab
        </ul>
      </div>
    );

    if ($form eq "s1") {
        print encode_utf8(qq(
      <div class="formOn">
	<form name="barcode" action="$this_script" method="get" accept-charset="UTF-8">
	    <input type="hidden" name="search" value="s1">
	  <div>
            <label for="bcStart">$Lang::string_bc_start</label>
          </div>
	  <div class="inputStyle">
            <input id="bcStart" type="text" name="bcs" value="" size="20">
          </div>
	  <div>
            <label for="bcEnd">$Lang::string_bc_end</label>
          </div>
	  <div class="inputStyle">
            <input id="bcEnd" type="text" name="bce" value="" size="20">
          </div>
          <div class="formCheckBoxes">
        ));
        my $checked_box = '';
        if ($show_charge_stats eq 'Y') {
            $checked_box = qq(checked="checked");
        } else {
            $checked_box = '';
        }
        print encode_utf8(qq(
	    <input type="checkbox" name="charges" id="charges" class="checkbox" value="Y" $checked_box><label for="charges">$Lang::string_ch_full</label><br>
        ));
        $checked_box = '';
        if ($show_browse_stats eq 'Y') {
            $checked_box = qq(checked="checked");
        } else {
            $checked_box = '';
        }
        print encode_utf8(qq(
	    <input type="checkbox" name="browses" id="browses" class="checkbox"  value="Y" $checked_box><label for="browses">$Lang::string_br_full</label><br>
        ));
    $checked_box = '';
        if ($show_item_status eq 'Y') {
            $checked_box = qq(checked="checked");
        } else {
            $checked_box = '';
        }
        print encode_utf8(qq(
	    <input type="checkbox" name="status" id="status" class="checkbox" value="Y" $checked_box><label for="status">$Lang::string_st_full</label>
        ));
	   # <input type="checkbox" name="boxes" id="boxes" class="checkbox" value="Y"><a href="$this_script?show=help&amp;topic=boxes"><label for="boxes">place holders</label></a>
        $checked_box = '';
        print encode_utf8(qq(
          </div>
          <div class="formSubmit">
	    <input type="submit" class="button" value="$Lang::string_form_submit">
          </div>
          <div class="clear">
	    <input type="hidden" name="stpt" value="1">
            $hidden_inputs
          </div>
	</form>
      </div>
        ));
    }
    if ($form eq "s2") {
        print encode_utf8(qq(
      <div class="formOn">
	<form name="callNumber" action="$this_script" method="get" accept-charset="UTF-8">
	    <input type="hidden" name="search" value="s2">
	  <div>
            <label for="callnoStart">$Lang::string_callno_start</label>
          </div>
	  <div class="inputStyle">
             <input id="callnoStart" type="text" name="cns" value="" size="20">
          </div>
	  <div>
            <label for="callnoEnd">$Lang::string_callno_end</label>
          </div>
	  <div class="inputStyle">
            <input id="callnoEnd" type="text" name="cne" value="" size="20">
          </div>
        ));
        print encode_utf8(qq(
	  <div>
            <label for="loc_id">$Lang::string_callno_location</label>
          </div>
          <div>
          <select name="loc_id" id="loc_id">
        ));
        my @sorted = sort (keys %location_list);
        foreach my $key (@sorted) {
            my $selected = '';
            if ($location_id eq "$location_list{$key}") {
                $selected = 'selected="selected" ';
            }
            # This adds Unicode LRM (LEFT-TO-RIGHT MARK) after ASCII only text
            my $display_key = $key;
            if ($Lang::text_direction =~ /RTL/i) {
                unless ($key !~ /[\x20-\x7E]/) {
                    $display_key .= "&#x200E;";
                }
            }
	    print encode_utf8(qq(      <option $selected value="$location_list{$key}">$display_key</option>
            ));
        }
        print encode_utf8(qq(
          </select>
          </div>
	  <div>
            <label for="callnoClass">$Lang::string_callno_class</label>
          </div>
	  <div>
          <select id="callnoClass" name="class_type">
	    <option value="LC">Library of Congress</option>
	  </select>
          </div>
          <div class="formCheckBoxes">
        ));
        my $checked_box = '';
        if ($show_charge_stats eq 'Y') {
            $checked_box = qq(checked="checked");
        } else {
            $checked_box = '';
        }
        print encode_utf8(qq(
	    <input type="checkbox" name="charges" id="charges" class="checkbox" value="Y" $checked_box><label for="charges">$Lang::string_ch_full</label><br>
        ));
        $checked_box = '';
        if ($show_browse_stats eq 'Y') {
            $checked_box = qq(checked="checked");
        } else {
            $checked_box = '';
        }
        print encode_utf8(qq(
	    <input type="checkbox" name="browses" id="browses" class="checkbox" value="Y" $checked_box><label for="browses">$Lang::string_br_full</label><br>
        ));
        $checked_box = '';
        if ($show_item_status eq 'Y') {
            $checked_box = qq(checked="checked");
        } else {
            $checked_box = '';
        }
        print encode_utf8(qq(
	    <input type="checkbox" name="status" id="status" class="checkbox" value="Y" $checked_box><label for="status">$Lang::string_st_full</label>
          </div>
          <div class="formSubmit">
	    <input type="submit" class="button" value="$Lang::string_form_submit">
          </div>
          <div class="clear">
	    <input type="hidden" name="stpt" value="1">
            $hidden_inputs
          </div>
	</form>
      </div>
        ));
	    #<input type="checkbox" name="boxes" id="boxes" class="checkbox" value="Y"><a href="$this_script?show=help&amp;topic=boxes"><label for="boxes">place holders</label></a>
    }
    PrintTail();
    exit (0);
}


##########################################################
#  GenRandomList
##########################################################

sub GenRandomList {
    my ($count) = @_;
    $count++;

    # Connect to Oracle database
    ConnectVygrDB();

    # Get upper maximum value of Item ID 
    $sth = $dbh->prepare("select max(item_id) from $db_name.item_barcode") 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;

    my ($upper_bound_item_id) = $sth->fetchrow_array();

    # $random_item_id = int(rand($upper_bound_item_id));

    unless ($random_item_id =~ /^\d+$/) {
        $random_item_id = int(rand($upper_bound_item_id));
        $ENV{'QUERY_STRING'} .= "&itemid=$random_item_id";
    }

    # Get location info for this random item 
    $sth = $dbh->prepare("select
                           location_id,
                           location_name,
                           location_display_name
                         from
                           $db_name.item, 
                           $db_name.location 
                         where
                           item.perm_location = location.location_id and
                           item.item_id = '$random_item_id'") 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;

    my ($location_id, $location_name, $location_display_name) = $sth->fetchrow_array();

    # Get Call Number start for this item 
    $sth = $dbh->prepare("select
                           normalized_call_no
                         from
                           $db_name.mfhd_item, 
                           $db_name.mfhd_master 
                         where
                           mfhd_item.mfhd_id = mfhd_master.mfhd_id and 
                           mfhd_master.mfhd_id = '$random_item_id' 
                           ") 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;

    my ($start_call_no) = $sth->fetchrow_array();

    unless (defined($start_call_no)) {
        if ($count < 6) {
            GenRandomList($count);
        } else {
            ErrorPage("$Lang::string_random_fail");
        }
    }

    my $get_end_call_no = qq[
        select max(normalized_call_no) from (select
                  normalized_call_no,
                  RowNum
                from
                  $db_name.mfhd_master 
                where
                  mfhd_master.location_id = '$location_id' and
                  mfhd_master.normalized_call_no > '$start_call_no' 
                order by
                  mfhd_master.normalized_call_no)
        where RowNum <= $recs_per_page 
    ];

    # Get Call Number end for this item 
    $sth = $dbh->prepare("$get_end_call_no") 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;

    my ($end_call_no) = $sth->fetchrow_array();

    DisconnectVygrDB();

    if ($start_call_no && $end_call_no && $location_id) {
        GetShelfList($location_id, $location_name, $start_call_no, $end_call_no, $location_display_name);
    } else {
        ErrorPage("$Lang::string_random_fail");
    }

}


##########################################################
#  ValidateData
##########################################################

sub ValidateData {
    if ($search_type eq "s1") {
        $barcode_start =~ s/\s//g;
        $barcode_end   =~ s/\s//g;
        if ($barcode_start =~ /\W/) {
            ErrorPage("<p>$Lang::string_bc_bad_pre</p><p>$barcode_start</p><p>$Lang::string_bc_bad_post</p>");
        } elsif ($barcode_end =~ /\W/) {
            ErrorPage("<p>$Lang::string_bc_bad_pre</p><p>$barcode_end</p><p>$Lang::string_bc_bad_post</p>");
        }
        if ($barcode_start && $barcode_end) {
            DoPrelimWork1();
        } elsif ($barcode_start || $barcode_end) {
            if ($barcode_start) {
	        $barcode_end = $barcode_start;
            } else {
	        $barcode_start = $barcode_end;
            }
            DoPrelimWork1();
        } else {
            $show_page = "s1";
            PrintSearchForm("s1");
        }
    } elsif ($search_type eq 's2') {
	if ($call_num_start && $call_num_end) {
            DoPrelimWork2();
	} elsif ($call_num_start || $call_num_end) {
            if ($call_num_start) {
	        $call_num_end = $call_num_start;
            } else {
	        $call_num_start = $call_num_end;
            }
            DoPrelimWork2();
	} else{
            $show_page = "s2";
            PrintSearchForm("s2");
	}
    }
}


##########################################################
#  NormalizeLC
##########################################################

sub NormalizeLC {
    my ($lc_call_no_orig) = @_;
    my ($initial_letters, $class_number, $decimal_number, $cutter_1_letter,
	$cutter_1_number, $cutter_2_letter, $cutter_2_number, $pub_year_plus,
	$normalized, $lc_call_no);
    # Remove any initial white space
    $lc_call_no = $lc_call_no_orig;
    $lc_call_no =~ s/^\s*//g;
    # Convert all alpha to uppercase
    $lc_call_no = uc($lc_call_no);
    if ($lc_call_no =~ /^([A-Z]{1,3})\s*(\d*)\s*\.*(\d*)\s*\.*\s*([A-Z]*)(\d*)\s*([A-Z]*)\s*(\d*)\s*(\w*)$/) {
	$initial_letters = $1;
	$class_number    = $2;
	$decimal_number  = $3;
	$cutter_1_letter = $4;
	$cutter_1_number = $5;
	$cutter_2_letter = $6;
	$cutter_2_number = $7;
	$pub_year_plus   = $8;
        if ((! $cutter_2_letter) && $cutter_2_number) {
            $pub_year_plus = $cutter_2_number;
            $cutter_2_number = '';
        }
        if ($class_number) {
            $class_number = sprintf("%5s", $class_number);
        }
        $decimal_number = sprintf("%-12s", $decimal_number);
        if ($cutter_1_number) {
            $cutter_1_number = " $cutter_1_number";
        }
        if ($cutter_2_letter) {
            $cutter_2_letter = "   $cutter_2_letter";
        }
        if ($cutter_2_number) {
            $cutter_2_number = " $cutter_2_number";
        }
        if ($pub_year_plus) {
	    if ($pub_year_plus =~ /^(\d+)(\D+)$/) {
		$pub_year_plus = "$1" . " $2"; 
	    }
            $pub_year_plus = "   $pub_year_plus";
        }
        $normalized = "$initial_letters" . "$class_number" . "$decimal_number" . "$cutter_1_letter" . "$cutter_1_number" . "$cutter_2_letter" . "$cutter_2_number" . "$pub_year_plus";
        return "$normalized";
    } else {
	ErrorPage("<p>$Lang::string_cn_error</p><p>$lc_call_no_orig</p>");
    }
}


##########################################################
#  DoPrelimWork1
##########################################################

sub DoPrelimWork1 {

    # Connect to Oracle database
    ConnectVygrDB();

    # Prepare the first preliminary SQL statement
    my $sth = $dbh->prepare(ConstructSQLprelim($barcode_start)) 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;

    my ($start_call_num, $start_perm_loc, $start_temp_loc, $start_loc,
          $end_call_num,   $end_perm_loc,   $end_temp_loc,   $end_loc, 
	$location);

    while( my (@entry) = $sth->fetchrow_array() ) {
        $start_call_num = $entry[0];
        $start_perm_loc = $entry[1];
        $start_temp_loc = $entry[2];
        if ($start_temp_loc) {
	    $start_loc = $start_temp_loc;
        } else {
	    $start_loc = $start_perm_loc;
        }
    }
    if (! $start_call_num) {
	ErrorPage("<p>$Lang::string_bc_bad_pre</p><p>$barcode_start</p><p>$Lang::string_bc_bad_post</p>");
    }

    # Prepare the second preliminary SQL statement
    $sth = $dbh->prepare(ConstructSQLprelim($barcode_end)) 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;

    while( my (@entry) = $sth->fetchrow_array() ) {
        $end_call_num = $entry[0];
        $end_perm_loc = $entry[1];
        $end_temp_loc = $entry[2];
        if ($end_temp_loc) {
	    $end_loc = $end_temp_loc;
        } else {
	    $end_loc = $end_perm_loc;
        }
    }
    if (! $end_call_num) {
	ErrorPage("<p>$Lang::string_bc_bad_pre</p><p>$barcode_end</p><p>$Lang::string_bc_bad_post</p>");
    }

    if ($start_loc ne $end_loc) {
	my $error = "<p>$Lang::string_loc_mismatch</p><p>$Lang::string_loc_mismatch_desc</p>";
	ErrorPage($error);
    } else {
	$location = $start_loc;
    }

    $sth = $dbh->prepare("select location_name, location_display_name from $db_name.location where location_id = '$location'"); 
    $sth->execute || die $dbh->errstr;
    my ($location_name, $location_display_name) = $sth->fetchrow_array();

    if ($start_call_num gt $end_call_num) {
	my $temp_call_num = $end_call_num;
	$end_call_num = $start_call_num;
	$start_call_num = $temp_call_num;
    }

    DisconnectVygrDB();

    GetShelfList($location, $location_name, $start_call_num, $end_call_num, $location_display_name); 
}


##########################################################
#  DoPrelimWork2
##########################################################

sub DoPrelimWork2 {

    # Connect to Oracle database
    ConnectVygrDB();
    
    # Normalize the call numbers
    $call_num_start = NormalizeLC($call_num_start);
    $call_num_end   = NormalizeLC($call_num_end);

    if ($call_num_start gt $call_num_end) {
        my $temp_call_num = $call_num_end;
        $call_num_end     = $call_num_start;
        $call_num_start   = $temp_call_num;
    }

    # Prepare the first preliminary SQL statement
    my $sth = $dbh->prepare("select location_name, location_display_name from $db_name.location where location_id = '$location_id'") 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;

    my ($location_name, $location_display_name) = $sth->fetchrow_array();

    DisconnectVygrDB();

    GetShelfList($location_id, $location_name, $call_num_start, $call_num_end, $location_display_name); 
}


##########################################################
#  GetShelfList
##########################################################

sub GetShelfList {
    my ($location, $location_display, $start_call_num, $end_call_num, $location_display_name) = @_;

    # Connect to Oracle database
    ConnectVygrDB();

    # Prepare the shelf list SQL statement
    $sth = $dbh->prepare(ConstructSQLlist($location,$start_call_num,$end_call_num)) 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;

    PrintHead("$Lang::string_shelf_list");
    my $logo_query_string = '';

    $location_display_name =~ s/\&/&amp;/g;

    my $table_heading = qq(
    <tr id="shelfList">
        <th scope="col"><abbr title="$Lang::string_number_full">$Lang::string_number_abbrev</abbr></th>
    );

    if ($show_charge_stats eq "Y") {
        $table_heading .= qq(
        <th scope="col"><abbr title="$Lang::string_ch_full">$Lang::string_ch_abbrev</abbr></th>
        );
    }
    if ($show_browse_stats eq "Y") {
        $table_heading .= qq(
        <th scope="col"><abbr title="$Lang::string_br_full">$Lang::string_br_abbrev</abbr></th>
        );
    }

    if ($show_item_status eq "Y") {
        $table_heading .= qq(
        <th><abbr title="$Lang::string_st_full">$Lang::string_st_abbrev</abbr></th>
        );
    }
#    if ($show_boxes eq "Y") {
#	$table_heading .= qq(
#        <th scope="col"></th>
#        );
#    }
	$table_heading .= qq(\t<th scope="col"></th>\n);

    my $toggle_purposes_url     = "$this_script?$ENV{'QUERY_STRING'}";

    my $mouse_over_toggle       = '';
    my $call_number_plus_toggle = '';
    my $title_callno_toggle_btn = '';
    my $mouse_over_toggle_url   = "$toggle_purposes_url"; 
    my $callno_plus_toggle_url  = "$toggle_purposes_url"; 

    if ($mouse_over eq "Y") {
        $mouse_over_toggle_url =~ s/omoo=Y/omoo=N/;
        $mouse_over_toggle_url =~ s/\&/&amp;/g;
        $mouse_over_toggle = qq(<a href="$mouse_over_toggle_url" title="$Lang::string_mouse_over_tog"><span class="omooOn">+/-</span></a>);
    } else {
        if ($mouse_over_toggle_url =~ /omoo=N/) {
            $mouse_over_toggle_url =~ s/omoo=N/omoo=Y/;
        } else {
            $mouse_over_toggle_url .= '&omoo=Y';
        }
        $mouse_over_toggle_url =~ s/&cnplus=[YN]//;;
        $mouse_over_toggle_url =~ s/\&/&amp;/g;
        $mouse_over_toggle = qq(<a href="$mouse_over_toggle_url" title="$Lang::string_mouse_over_tog"><span class="omooOff">+/-</span></a>);
    }

    if ($show_callno_plus eq "Y") {
        $callno_plus_toggle_url =~ s/cnplus=Y/cnplus=N/;
        $callno_plus_toggle_url =~ s/\&/&amp;/g;
        $call_number_plus_toggle = qq(<a href="$callno_plus_toggle_url" title="$Lang::string_callno_plus_tog">&minus;</a>);
    } else {
        if ($callno_plus_toggle_url =~ /cnplus=N/) {
            $callno_plus_toggle_url =~ s/cnplus=N/cnplus=Y/;
        } else {
            $callno_plus_toggle_url .= '&cnplus=Y';
        }
        $callno_plus_toggle_url      =~ s/&omoo=[YN]//;;
        $callno_plus_toggle_url =~ s/\&/&amp;/g;
        $call_number_plus_toggle = qq(<a href="$callno_plus_toggle_url" title="$Lang::string_callno_plus_tog">+</a>);
    }

    my $switch_mode_link = "$toggle_purposes_url";
    if ($list_display eq "2") {
        if ($switch_mode_link =~ /mode=2/) {
            $switch_mode_link =~ s/mode=2/mode=1/g;
        } else {
            $switch_mode_link .= '&mode=1';
        }
        $switch_mode_link =~ s/\&/&amp;/g;;
        $table_heading .= qq(
        <th scope="col" id="listHeader">$Lang::string_titles</th>
      </tr>
        );
        $title_callno_toggle_btn = qq(<a href="$switch_mode_link" title="$Lang::string_call_no_blurb">$Lang::string_call_no</a>);
    } else {
        if ($switch_mode_link =~ /mode=1/) {
            $switch_mode_link =~ s/mode=1/mode=2/g;
        } else {
            $switch_mode_link .= '&mode=2';
        }
        $switch_mode_link =~ s/\&/&amp;/g;;
        $table_heading .= qq(
        <th scope="col" id="listHeader">$Lang::string_call_no <span class="cnplusToggle">$call_number_plus_toggle</span></th>
      </tr>
        );
        $title_callno_toggle_btn = qq(<a href="$switch_mode_link" title="$Lang::string_titles_blurb">$Lang::string_titles</a>);
    } 

    # This adds Unicode LRM (LEFT-TO-RIGHT MARK) after ASCII only text
    if ($Lang::text_direction =~ /RTL/i) {
        unless ($location_display_name !~ /[\x20-\x7E]/) {
            $location_display_name .= "&#x200E;";
        }
    }

    print encode_utf8(qq(
    <h1>$Lang::string_shelf_list</h1>
    <div id="titleCallNoToggle">$title_callno_toggle_btn</div>
    $Lang::string_location <abbr title="$location_display_name">$location_display</abbr>
    <form action="$this_script" method="get" accept-charset="UTF-8">
      <input type="hidden" name="show" value="mail">
    <table summary="$Lang::string_shelf_list_table">
    <thead>
    $table_heading
    </thead>
    <tbody>
    ));

    my (@stash_of_rows, $array_ref);
    while ( $array_ref = $sth->fetchrow_arrayref ) {
	push @stash_of_rows, [ @$array_ref ];
    }

    my $row_total = @stash_of_rows;

    my ($item_id, 
	$item_id_p, 
	$mfhd_id, 
	$mfhd_id_p, 
	$hist_charges, 
	$hist_charges_p, 
	$hist_browses, 
	$hist_browses_p, 
	$holds_placed, 
	$holds_placed_p, 
	$recalls_placed, 
	$recalls_placed_p, 
	$status_abbrev,
	$status_abbrev_p,
	$normalized_call_no, 
	$normalized_call_no_p, 
	$display_call_no, 
	$display_call_no_p, 
	$enum, 
	$enum_p, 
	$chron, 
	$chron_p, 
	$year, 
	$year_p, 
	$copy_number, 
	$copy_number_p,
        $title_brief, 
        $title_brief_p 
	);

    my $row_count = 0;
    my $true_count = 0;
    foreach $array_ref ( @stash_of_rows ) {
	$row_count++; 
	$item_id	    = decode_utf8($array_ref->[0]);
	$mfhd_id	    = decode_utf8($array_ref->[1]);
	$hist_charges	    = decode_utf8($array_ref->[2]);
	$hist_browses	    = decode_utf8($array_ref->[3]);
	$holds_placed	    = decode_utf8($array_ref->[4]);
	$recalls_placed	    = decode_utf8($array_ref->[5]);
	if ($array_ref->[6]) {
	    $status_abbrev  = decode_utf8(StatusAbbrev($array_ref->[6]));
	} else {
	    $status_abbrev  = '';
	}
	$normalized_call_no = decode_utf8($array_ref->[7]);
	$display_call_no    = decode_utf8($array_ref->[8]);
#  Debugging
#	print "$row_count: $display_call_no<br>\n";;
	$enum		    = decode_utf8($array_ref->[9]);
	$chron		    = decode_utf8($array_ref->[10]);
	$year		    = decode_utf8($array_ref->[11]);
	$copy_number	    = decode_utf8($array_ref->[12]);
	$title_brief	    = decode_utf8($array_ref->[13]);
        $title_brief        =~ s# $##;
        $title_brief        =~ s# /$##;
        my $title_max       = '';
        if ($ShelfListerIni::title_truncation =~ /\D/) {
            $title_max       = "90";
        } else {
            $title_max      = $ShelfListerIni::title_truncation;
        }
        if (length($title_brief) > $title_max) {
            $title_brief        = substr($title_brief,0,$title_max);
            $title_brief        =~ s/ \S*$//;
            $title_brief       .= " ...";
        }
        $title_brief        =~ s/\'/&rsquo;/g;

	if ($row_count > 1 ) {
	    if ((! $item_id) || $item_id ne $item_id_p) {
	        if ( ! ($status_abbrev_p =~ /W/)) {
    	            $true_count++;
		    if ($true_count >= $starting_pnt &&
	                $true_count <= $ending_pnt) {
	                PrintRow($item_id_p, $mfhd_id_p, $status_abbrev_p,
		        $hist_charges_p, $hist_browses_p, $holds_placed_p,
		        $recalls_placed_p, $display_call_no_p, $enum_p, 
			$chron_p, $year_p, $copy_number_p, $true_count, 
                        $title_brief_p);
		    }
	        }
	    }
	}

	if ($status_abbrev_p && $item_id eq $item_id_p) {
	    if ($status_abbrev && $status_abbrev ne $status_abbrev_p) {
	        $status_abbrev_p   .= ",$status_abbrev";
	    }
	} else {
	    $status_abbrev_p    = $status_abbrev;
	}
	$item_id_p	    	= $item_id;
	$mfhd_id_p		= $mfhd_id;
	$hist_charges_p		= $hist_charges;
	$hist_browses_p		= $hist_browses;
	$holds_placed_p		= $holds_placed;
	$recalls_placed_p	= $recalls_placed;
	$normalized_call_no_p	= $normalized_call_no;
	$display_call_no_p	= $display_call_no;
	$enum_p			= $enum;
	$chron_p		= $chron;
	$year_p			= $year;
	$copy_number_p		= $copy_number;
	$title_brief_p		= $title_brief;

	if ($row_count == $row_total) {
	    if ( ! ($status_abbrev_p =~ /W/)) {
    	        $true_count++;
		if ($true_count >= $starting_pnt &&
	            $true_count <= $ending_pnt) {
	            PrintRow($item_id_p, $mfhd_id_p, $status_abbrev_p,
		    $hist_charges_p, $hist_browses_p, $holds_placed_p,
		    $recalls_placed_p, $display_call_no_p, $enum_p, 
		    $chron_p, $year_p, $copy_number_p, $true_count,
                    $title_brief_p);
		}
	    }
	}
	
    }

    print qq(
    </tbody>
  </table>
  </form>
    );

#    //mdd Previous button... more testing?
    my $prev_next = '';
    if ($ending_pnt > $recs_per_page) {
        my $prev_starting_pnt = $starting_pnt - $recs_per_page;
	my $prev_number = $recs_per_page;
        if ($prev_starting_pnt < 1) {
            $prev_starting_pnt = 1;
	    $prev_number = $ending_pnt - $recs_per_page;
        }
        my $query_string = $ENV{'QUERY_STRING'};
        $query_string =~ s/&stpt=[\d]*/&stpt=$prev_starting_pnt/;  
        $query_string =~ s/\&/&amp;/g;  
        #$prev_next = qq(<a class="prevBtn" href="$this_script?$query_string"><span class="fauxButton">&lt; $Lang::string_prev $prev_number</span></a>);
        $prev_next = qq(<a class="prevBtn" href="$this_script?$query_string"><span class="fauxButton">&lt; $Lang::string_prev</span></a>);
    }

    if ($true_count > $ending_pnt) {
	my $new_starting_pnt = $ending_pnt + 1;
	my $next_number = $recs_per_page;
        if ($true_count - $ending_pnt <= $recs_per_page) {
	    $next_number = $true_count - $ending_pnt;
	}
        my $query_string = $ENV{'QUERY_STRING'};
	$query_string =~ s/&stpt=[\d]*/&stpt=$new_starting_pnt/;
        $query_string =~ s/\&/&amp;/g;  
	#$prev_next .= qq(<a class="nextBtn" href="$this_script?$query_string"><span class="fauxButton">$Lang::string_next $next_number &gt;</span></a>);
	$prev_next .= qq(<a class="nextBtn" href="$this_script?$query_string"><span class="fauxButton">$Lang::string_next &gt;</span></a>);
    }

    if ($prev_next) {
        print qq(<div class="prevNext">$prev_next</div>);
    }
    if ($true_count < 1 ) {
        my $message .= qq(
         <div class="margin">
           <h1 class="error">$Lang::string_no_results</h1>
            <p>$Lang::string_no_results_desc</p>
         );
	if ($search_type eq 's2') {
	    $message .= qq(<p>$Lang::string_no_results_loc</p>);
        }
        $message .= qq(
           <div><input type="button" value="$Lang::string_back" class="button" onClick="history.go\(-1\);"></div>
           </div>
        );
        print $message;
    }

    PrintTail();

    DisconnectVygrDB();
}


##########################################################
#  ShowRecordMFHD
##########################################################

sub ShowRecordMFHD {
    # Connect to Oracle database
    ConnectVygrDB();

    # Prepare the first preliminary SQL statement
    my $sth = $dbh->prepare(ConstructSQLmfhd($record_number)) 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;

    PrintHead("$Lang::string_item_view");
    print qq(
      <h1>$Lang::string_item_view</h1>
      $back_button
    );
    my ($call_number, $title, $author, $edition, $bib_id, $mfhd_id, $isbn);
    while( my (@entry) = $sth->fetchrow_array() ) {
	$call_number    = decode_utf8($entry[0]);
	$title 	        = decode_utf8($entry[1]);
	$author         = decode_utf8($entry[2]);
	$edition        = decode_utf8($entry[3]);
	$bib_id         = decode_utf8($entry[4]);
	$mfhd_id        = decode_utf8($entry[5]);
	$isbn           = decode_utf8($entry[6]);
    }

    # Note: should really use "pass by reference" to pass the %barcode
    # array to subroutine, but this syntax seems to work in this case.
    PrintSaveForm($bib_id, $mfhd_id, "", $call_number, "");

    # This adds Unicode LRM (LEFT-TO-RIGHT MARK) after ASCII only text
    if ($Lang::text_direction =~ /RTL/i) {
        unless ($title !~ /[\x20-\x7E]/) {
            $title .= "&#x200E;";
        }
        unless ($call_number !~ /[\x20-\x7E]/) {
            $call_number .= "&#x200E;";
        }
    }

    print encode_utf8(qq(
         <div class="itemNum">$call_number</div>
         <div class="itemTitle>$title &nbsp; $edition</div>
         <div class="message">$Lang::string_no_item_record</div>
         <div id="lookUp" class="topBorder">
           $Lang::string_look_up_in
           <ul>
             <li>
               <a href="$ShelfListerIni::webvoyage_server_link$bib_id" target="catalog">$Lang::voyager_record_link_text</a>
             </li>
    ));

    $isbn = MungeISBN($isbn);

    if ($isbn) {
        my $worldcat_link_url = $ShelfListerIni::worldcat_link . $isbn;
        if ($ShelfListerIni::worldcat_link_location) {
            $worldcat_link_url .= "&amp;loc=" . $ShelfListerIni::worldcat_link_location;
        }
        print qq(
             <li>
               <a href="$worldcat_link_url" target="worldcat">$Lang::worldcat_record_link_text</a>
             </li>
        );
    }

    if ($isbn && $ShelfListerIni::google_link) {
        my $google_link_url = $ShelfListerIni::google_link . $isbn;
        print qq(
             <li>
               <a href="$google_link_url" target="google">$Lang::google_record_link_text</a>
             </li>
        );
    }
    print qq(
           </ul>
    );

    PrintTail();

    DisconnectVygrDB();
}


##########################################################
#  MungeISBN
##########################################################

sub MungeISBN {
    my ($isbn) = @_;
    $isbn =~ s/([\dX]{10})[^\dX].*$/$1/;
    $isbn =~ s/([\dX]{13})[^\dX].*$/$1/;

    if ($isbn =~ /^[\dX]*$/){
        if (length($isbn) == 10 || length($isbn) == 13) {
            return($isbn);
        }
    }
    return('');
}


##########################################################
#  ShowRecordItem
##########################################################

sub ShowRecordItem {
    # Connect to Oracle database
    ConnectVygrDB();

    # Prepare the first preliminary SQL statement
    my $sth = $dbh->prepare(ConstructSQLitem($record_number)) 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;

    PrintHead("$Lang::string_item_view");
    print qq(
      <h1>$Lang::string_item_view</h1>
      $back_button
    );
    my ($call_number, $enum, $chron, $year, $copy_number, $title, $author, $edition, %status, %barcode, $bib_id, $mfhd_id, $item_id, $item_type_name, $isbn, $hist_charges, $hist_browses, $item_note);
    while( my (@entry) = $sth->fetchrow_array() ) {
	$call_number 	= decode_utf8($entry[0]);
	$enum	 	= decode_utf8($entry[1]);
	$chron	 	= decode_utf8($entry[2]);
	$year	 	= decode_utf8($entry[3]);
	$copy_number 	= decode_utf8($entry[4]);
	$title 		= decode_utf8($entry[5]);
	#$title 		= $entry[5];
	$author 	= decode_utf8($entry[6]);
	$edition 	= decode_utf8($entry[7]);
	%status  = (%status,  (decode_utf8($entry[8])  => decode_utf8($entry[9])));
	%barcode = (%barcode, (decode_utf8($entry[10]) => decode_utf8($entry[11])));
	$bib_id 	= decode_utf8($entry[12]);
	$mfhd_id 	= decode_utf8($entry[13]);
	$item_id 	= decode_utf8($entry[14]);
	$item_type_name = decode_utf8($entry[15]);
	$isbn           = decode_utf8($entry[16]);
	$hist_charges   = decode_utf8($entry[17]);
	$hist_browses   = decode_utf8($entry[18]);
        $item_note      = decode_utf8($entry[19]);
    }
    if ($enum) {
	$call_number .= " $enum";
    }
    if ($chron) {
	$call_number .= " $chron";
    }
    if ($year) {
	$call_number .= " $year";
    }
    if ($copy_number && $copy_number > 1) {
	$call_number .= " c.$copy_number";
    }

    # Note: Should really use "pass by reference" to pass the %barcode
    # array to subroutine, but this syntax seems to work in this case.
    PrintSaveForm($bib_id, $mfhd_id, $item_id, $call_number, %barcode);

    # This adds Unicode LRM (LEFT-TO-RIGHT MARK) after ASCII only text
    if ($Lang::text_direction =~ /RTL/i) {
        unless ($title !~ /[\x20-\x7E]/) {
            $title .= "&#x200E;";
        }
        unless ($call_number !~ /[\x20-\x7E]/) {
            $call_number .= "&#x200E;";
        }
        unless ($item_note !~ /[\x20-\x7E]/) {
            $item_note .= "&#x200E;";
        }
    }

    print encode_utf8(qq(
         <div class="itemNum">$call_number</div>
         <div class="itemTitle">$title &nbsp; $edition</div>
         <div class="itemStats">
           <span class="label">$Lang::string_ch_full:</span>
           <span class="data">$hist_charges</span> 
         <br>
           <span class="label">$Lang::string_br_full:</span>
           <span class="data">$hist_browses</span> 
         </div>
    ));

    if (%status) {
        foreach my $key (keys (%status)) {
            print qq(
              <div class="itemStatus">
                <span class="label">$Lang::string_st_full:</span>
                <span class="data">$key</span> <span>$status{$key}</span> 
              </div>
            );
        }
    }

    if (%barcode) {
        foreach my $key (sort keys (%barcode)) {
            print qq(
              <div class="itemBarcode">
                <span class="label">$Lang::string_barcode:</span>
                <span class="data">$key</span> 
              </div>
            );
        }
    }

    if ($item_note) {
        print qq(
              <div class="itemNote">
                <span class="">$Lang::string_item_note:</span> 
                <span>$item_note</span>
              </div>
        );
    }

    print qq(
         <div id="lookUp" class="topBorder">
           $Lang::string_look_up_in
           <ul>
             <li>
               <a href="$ShelfListerIni::webvoyage_server_link$bib_id" target="catalog">$Lang::voyager_record_link_text</a>
             </li>
    );

    $isbn = MungeISBN($isbn);

    if ($isbn && $ShelfListerIni::worldcat_link) {
        my $worldcat_link_url = $ShelfListerIni::worldcat_link . $isbn;
        if ($ShelfListerIni::worldcat_link_location) {
            $worldcat_link_url .= "&amp;loc=" . $ShelfListerIni::worldcat_link_location;
        }
        print qq(
             <li>
               <a href="$worldcat_link_url" target="worldcat">$Lang::worldcat_record_link_text</a>
             </li>
        );
    }

    if ($isbn && $ShelfListerIni::google_link) {
        my $google_link_url = $ShelfListerIni::google_link . $isbn;
        print qq(
             <li>
               <a href="$google_link_url" target="google">$Lang::google_record_link_text</a>
             </li>
        );
    }
    print qq(
           </ul>
         </div>
    );

    PrintTail();

    DisconnectVygrDB();
}


##########################################################
#  ShowMailSave 
##########################################################

sub ShowMailSave {
     my $test = $ENV{'QUERY_STRING'};
     TestPage($test);
}


##########################################################
#  PrintSaveForm
##########################################################

sub PrintSaveForm {
    my ($bib_id, $mfhd_id, $item_id, $call_number, %barcode) = @_;
    my $save_to_file_barcode = '';
    foreach my $key (keys (%barcode)) {
	if ($barcode{$key} eq "Active") {        
            $save_to_file_barcode = $key;
        }
    }
    print qq(
	<form action="$this_script" method="get" accept-charset="UTF-8">
          <label for="save_status">$Lang::string_mark_status_label</label>
	  <select name="save_status" size="1" id="save_status">
    );
    foreach my $i (@save_stati) { 
	print "<option>$i</option>\n\t";
    }
    print qq(
	  </select>
	  <input type="submit" name="submit" class="button" value="&gt;">
          <br>
    );
    if ($update_ok eq "yes") {
        print qq(
	  <input type="radio" name="save_action" value="update">Update &nbsp;
	  <input type="radio" name="save_action" value="delete">Delete
	);
    }
    print qq(
	  <input type="hidden" name="save_bib_id" value="$bib_id">
	  <input type="hidden" name="save_mfhd_id" value="$mfhd_id">
	  <input type="hidden" name="save_item_id" value="$item_id">
	  <input type="hidden" name="save_call_no" value="$call_number">
	  <input type="hidden" name="save_barcode" value="$save_to_file_barcode">
	</form>\n\n);

}


##########################################################
#  SaveToFile
##########################################################

sub SaveToFile {
    my ($second, 
	$minute, 
	$hour,
	$day,
	$month,
	$year,
	$wday,
	$yday,
	$isdst) = localtime(time());
    $month +=    1;
    $year  += 1900;
    $day    = sprintf("%02d" , $day);
    $hour   = sprintf("%02d" , $hour);
    $minute = sprintf("%02d" , $minute);
    $second = sprintf("%02d" , $second);
    open (SAVEFILE, ">>$report_dir/$out_file")
        || ErrorPage("<p>Cannot open save file:<br>$report_dir/$out_file<br><strong>$!</strong></p>");
#        || die "Cannot create/open output file: $!";
    # Lock database file
    flock (SAVEFILE,2);
#    seek  (SAVEFILE,0,0);

    print SAVEFILE "$year-$month-$day $hour:$minute:$second|$save_bib_id|$save_mfhd_id|$save_item_id|$save_barcode|$save_status|$save_call_no\n";
    close (SAVEFILE);

    PrintHead();
    print qq(
    Item marked as <b>$save_status</b>
    );
    print qq(<br><br>Marking an item does not update the Voyager database.  It adds an entry to the <a href="$this_script?show=mif">Marked Items File</a>.);
    PrintTail();
}


##########################################################
#  DeleteFromFile
##########################################################

sub DeleteFromFile {

    open (SAVEFILE, "+< $report_dir/$out_file")
        || ErrorPage("<p>Marked Item File:<br>$report_dir/$out_file does not exist yet.<br><strong>$!</strong></p>");

    # Lock database file
    flock (SAVEFILE,2)
        || ErrorPage("<p>Delete action aborted, could not lock file:<br>$report_dir/$out_file<br><strong>$!</strong></p>");

#    cp ("$report_dir/$out_file", "$report_dir/$out_file.$$");

#    open (SAVEFILE, "> $report_dir/$out_file")
#        || ErrorPage("<p>Can't open <br>$report_dir/$out_file<br><strong>$!</strong></p>");

    open (TEMPFILE, ">$report_dir/$out_file.$$")
        || ErrorPage("<p>Cannot open temp file:<br>$report_dir/$out_file.$$<br><strong>$!</strong></p>");

    my $pr = 1;
    my $was_found = "no";
    while (<SAVEFILE>) {
	my ($date_stamp, $bib_id, $mfhd_id, $item_id, $barcode, 
	    $status, $call_number) = split(/\|/, $_); 
	if ($save_item_id && ($save_item_id eq $item_id)) {
	    $pr = 0;
	    $was_found = "yes";
	} elsif ($save_mfhd_id && ($save_mfhd_id eq $mfhd_id)) {
	    $pr = 0;
	    $was_found = "yes";
	} else {
	    $pr = 1;
	}
	print TEMPFILE if ($pr == 1);
    sleep 2;
    }

    rename ("$report_dir/$out_file.$$", "$report_dir/$out_file");

    close (SAVEFILE);
    close (TEMPFILE);

    if ($save_action eq "delete") {
	PrintHead();
    print qq(
    );
        if ($was_found eq "yes") {
	    print qq(All entries for item were deleted from the <a href="$this_script?show=mif">Marked Items File</a>.);
        } else {
	    print qq(Item was not in the <a href="$this_script?show=mif">Marked Items File</a>.);
        } 
	PrintTail();
    }
}


############################################################
#  PrintRow
############################################################
#

sub PrintRow {
    my ($item_id, 
	$mfhd_id, 
	$status_abbrev, 
	$hist_charges, 
	$hist_browses, 
	$holds_placed,
	$recalls_placed, 
	$display_call_no,
	$enum, 
	$chron, 
	$year, 
	$copy_number,
	$line_number,
        $title_brief) = @_;
        if ($line_number < 10) {
            $line_number = "&nbsp;&nbsp;$line_number";
        }
    my $checkbox_value = '';
    # Ugly hack for getting a proper border using RTL on IE
    if ($Lang::text_direction =~ /RTL/i) {
        $line_number = "&#x200B;" . $line_number . "&#x200B;";
    }
    print qq(\n    <tr class="recordRow">
         <td align="right" valign="top">);
    if ($item_id) {
	print qq(<a class="numLink" href="$this_script?record_type=item&amp;record_no=$item_id">$line_number</a>);
        $checkbox_value = "item$item_id";
    } else {
	print qq(<a class="numLink" href="$this_script?record_type=mfhd&amp;record_no=$mfhd_id">$line_number</a>);
        $checkbox_value = "mfhd$mfhd_id";
    }
    print "</td>";
    if ($show_charge_stats eq "Y") {
        print qq(\n\t<td align="right" valign="top">);
        print "$hist_charges";
        print "</td>";
    }
    if ($show_browse_stats eq "Y") {
        print qq(\n\t<td align="right" valign="top">);
        print "$hist_browses";
        print "</td>";
    }
    if ($show_item_status eq "Y") {
        print qq(\n\t<td align="center" valign="top">);
        print "<strong>$status_abbrev</strong>";
        print "</td>";
    }

    my $extra_item_info = '';
    if ($show_callno_plus eq "Y") {
        if ($enum) {
    	    $extra_item_info .= " $enum";
        }
        if ($chron) {
	    $extra_item_info .= " $chron";
        }
        if ($year) {
	    $extra_item_info .= " $year";
        }
        if ($copy_number && $copy_number > 1) {
	    $extra_item_info .= " c.$copy_number";
        }
        $extra_item_info    =~ s/\'/&rsquo;/g;
        $extra_item_info    =~ s/[\<\>\"]//g;
        if ($extra_item_info) {
            $extra_item_info    = qq(<span class="cnplusOn">$extra_item_info</span>);
        }
    }

    # This adds Unicode LRM (LEFT-TO-RIGHT MARK) after ASCII only text
    if ($Lang::text_direction =~ /RTL/i) {
        unless ($display_call_no !~ /[\x20-\x7E]/) {
            $display_call_no .= "&#x200E;";
        }
        unless ($extra_item_info !~ /[\x20-\x7E]/) {
            $extra_item_info .= "&#x200E;";
        }
        unless ($title_brief !~ /[\x20-\x7E]/) {
            $title_brief .= "&#x200E;";
        }
    }

    if ($show_boxes eq "Y") {
	#print qq(
        #    <td valign="top"><input type="checkbox"></td>
        #);
    }
	print qq(
            <td valign="top"><input title="$Lang::string_checkbox" type="checkbox" name="check" value="$checkbox_value"></td>
        );

    if ($list_display eq '2') {
        if ($mouse_over eq "Y") {
            print encode_utf8(qq(
                <td valign="top"><span class="listLine" onMouseOver="this.firstChild.nodeValue='$display_call_no';" onMouseOut="this.firstChild.nodeValue='$title_brief';">$title_brief</span>
            ));
        } else {
            print encode_utf8(qq(
                <td valign="top"><span class="listLine">$title_brief</span>
            ));
        }
    } else {
        if ($mouse_over eq "Y") {
            print encode_utf8(qq(
                <td valign="top"><span class="listLine" onMouseOver="this.firstChild.nodeValue='$title_brief';" onMouseOut="this.firstChild.nodeValue='$display_call_no';">$display_call_no</span> $extra_item_info
            ));
        } else {
            print encode_utf8(qq(
                <td valign="top"><span class="listLine">$display_call_no</span> $extra_item_info
            ));
        }
    }
    print qq(</td>\n    </tr>);
}


############################################################
#  StatusAbbrev
############################################################
#

sub StatusAbbrev {
    my ($status) = @_;
    my $status_abbrev = "O";
    my %item_stati = (
	'Not Charged'		=> '',
	'Charged'		=> 'C',
	'Renewed'		=> 'C',
	'Overdue'		=> 'C',
	'Recall Request'	=> 'C',
	'Hold Request'		=> 'C',
	'On Hold'		=> 'H',
	'In Transit'		=> 'T',
	'In Transit Discharged'	=> 'T',
	'In Transit On Hold'	=> 'T',
	'Discharged'		=> 'D',
	'Missing'		=> 'M',
	'Lost--Library Applied'	=> 'L',
	'Lost--System Applied'	=> 'L',
	'Withdrawn'		=> 'W',
	'At Bindery'		=> 'B',
	'Cataloging Review'	=> 'R',
	'Circulation Review'	=> 'R',
	'In Process'		=> 'P'
	);
    foreach my $stati_key (keys %item_stati) {
	if ($status eq $stati_key) {
	    $status_abbrev = $item_stati{$stati_key};
        } 
    }
    return($status_abbrev);
}


############################################################
#  ConnectVygrDB
############################################################
#
#  Connects to the Voyager database

sub ConnectVygrDB {
    my $oracle_host_info = '';
    if ($ShelfListerIni::oracle_server) {
        $oracle_host_info = "host=$ShelfListerIni::oracle_server;SID=$ShelfListerIni::oracle_sid"; 
        if ($ShelfListerIni::oracle_listener_port) {
            $oracle_host_info .= ";port=$ShelfListerIni::oracle_listener_port";
        }
    }
    $dbh = DBI->connect("dbi:Oracle:$oracle_host_info", $username, $password)
        || ErrorConfig("fatal", "Could not connect to Oracle database:", "$DBI::errstr");
}

############################################################
#  DisconnectVygrDB
############################################################
#
#  Exits gracefully from the Voyager database

sub DisconnectVygrDB {
    if ($sth) {
       $sth->finish();
    }
    $dbh->disconnect();
}


##########################################################
#  ConstructSQLitem
##########################################################

sub ConstructSQLitem{
    my ($record_number) = @_;
    return ("
    select
	mfhd_master.display_call_no,
	mfhd_item.item_enum,
	mfhd_item.chron,
	mfhd_item.year,
	item.copy_number,
	bib_text.title,
	bib_text.author,
	bib_text.edition,
	item_status_type.item_status_desc,
	item_status.item_status_date,
	item_barcode.item_barcode,
	item_barcode_status.barcode_status_desc,
	bib_master.bib_id,
	mfhd_master.mfhd_id,
	item.item_id,
	item_type.item_type_name,
	bib_text.isbn,
	item.historical_charges,
	item.historical_browses,
        item_note.item_note
    from
	$db_name.bib_text,
	$db_name.bib_master,
	$db_name.bib_mfhd,
	$db_name.item,
	$db_name.item_status,
	$db_name.item_status_type,
	$db_name.item_barcode,
	$db_name.item_barcode_status,
	$db_name.item_type,
	$db_name.item_note,
	$db_name.mfhd_item,
	$db_name.mfhd_master
    where
	bib_text.bib_id=bib_master.bib_id and
	bib_master.bib_id=bib_mfhd.bib_id and
	mfhd_master.mfhd_id=bib_mfhd.mfhd_id and
	mfhd_master.mfhd_id=mfhd_item.mfhd_id and
	mfhd_item.item_id=item.item_id and
	item.item_id=item_status.item_id and
	item.item_id=item_barcode.item_id and
	item.item_id=item_note.item_id(+) and
	item_barcode.barcode_status=item_barcode_status.barcode_status_type and
	item_status.item_status=item_status_type.item_status_type and
	item.item_id='$record_number'
    ");
}


##########################################################
#  ConstructSQLmfhd
##########################################################

sub ConstructSQLmfhd{
    my ($record_number) = @_;
    return ("
    select
	mfhd_master.display_call_no,
	bib_text.title,
	bib_text.author,
	bib_text.edition,
	bib_mfhd.bib_id,
	bib_mfhd.mfhd_id,
	bib_text.isbn
    from
	$db_name.bib_text,
	$db_name.bib_master,
	$db_name.bib_mfhd,
	$db_name.mfhd_master
    where
	bib_text.bib_id=bib_master.bib_id and
	bib_master.bib_id=bib_mfhd.bib_id and
	mfhd_master.mfhd_id=bib_mfhd.mfhd_id and
	mfhd_master.mfhd_id='$record_number'
    ");
}


##########################################################
#  ConstructSQLprelim
##########################################################

sub ConstructSQLprelim {
    my ($barcode) = @_;
    return ("
    select
	normalized_call_no,
        perm_location,
        temp_location
    from
	$db_name.item_barcode,
	$db_name.item,
	$db_name.mfhd_item,
	$db_name.mfhd_master
    where
	item_barcode.item_id=item.item_id and
	item.item_id=mfhd_item.item_id and
	mfhd_item.mfhd_id=mfhd_master.mfhd_id and
	item_barcode='$barcode'
    ");
}


##########################################################
#  ConstructSQLlist
##########################################################

sub ConstructSQLlist {
    my ($location,$start_call_num,$end_call_num) = @_;
    return ("
    select distinct
	item.item_id,
	mfhd_master.mfhd_id,
	item.historical_charges,
	item.historical_browses,
	item.holds_placed,
	item.recalls_placed,
	item_status_type.item_status_desc,
	mfhd_master.normalized_call_no,
	mfhd_master.display_call_no,
	mfhd_item.item_enum,
	mfhd_item.chron,
	mfhd_item.year,
	item.copy_number,
        bib_text.title_brief
    from
	$db_name.item,
	$db_name.item_status,
	$db_name.item_status_type,
	$db_name.mfhd_item,
	$db_name.mfhd_master,
	$db_name.bib_master,
	$db_name.bib_mfhd,
        $db_name.bib_text
    where
	bib_text.bib_id=bib_master.bib_id and
	bib_master.bib_id=bib_mfhd.bib_id and
	mfhd_master.mfhd_id=bib_mfhd.mfhd_id and
	mfhd_master.mfhd_id=mfhd_item.mfhd_id(+) and
	mfhd_item.item_id=item.item_id(+) and
	item.item_id=item_status.item_id(+) and
	item_status.item_status=item_status_type.item_status_type(+) and
	mfhd_master.suppress_in_opac not in 'Y' and
	bib_master.suppress_in_opac not in 'Y' and
	normalized_call_no between ('$start_call_num') and ('$end_call_num') and
	((item.temp_location = '$location') or
         (item.perm_location = '$location' and item.temp_location = '0') or
	 (mfhd_master.location_id = '$location' and mfhd_item.item_id is null))
    order by
	mfhd_master.normalized_call_no,
	mfhd_item.item_enum,
	mfhd_item.chron,
	mfhd_item.year,
	item.item_id
    ");
}



##########################################################
#  PrintHead
##########################################################
#
#  Outputs the top portion of the HTML code.

sub PrintHead {
    my ($sub_title) = @_;
    my $active_search = '';
    my $active_help   = '';
    my $search_link   = '';
    if ($show_page eq "s1" || $show_page eq "s2") {
        $active_search = 'class="activeMenu" ';
    } elsif ($show_page eq "help" || $show_page eq "mif") {
        $active_help   = 'class="activeMenu" ';
    } 
    if ($search_type eq "s1" || $search_type eq "s2") {
        $search_link = "?$ENV{'QUERY_STRING'}";
        $search_link =~ s/search=s/show=s/;
        $search_link =~ s/\&/&amp;/g;
    } else { 
        $search_link = "?show=s1";
    }
    my $css_main = InternalCSS();
    print "Content-type: text/html; charset=utf-8\n\n";
    print qq( 
$doc_type_def
<html lang="$Lang::language_code">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <meta http-equiv="Content-Script-Type" content="text/javascript">
  <meta name="viewport" content="width=device-width; initial-scale=1.0; maximum-scale=1.0">
  <title>$this_app : $sub_title</title>
  <meta name="DC.Title"       content="$this_app $version">
  <meta name="DC.Creator"     content="Michael Doran">
  <meta name="DC.Type"        content="Software">
  <meta name="DC.Source"      content="http://rocky.uta.edu/doran/shelflister/">
  <meta name="DC.Publisher"   content="University of Texas at Arlington Library"> 
  <meta name="DC.Rights"      content="Copyright 2003-2009 University of Texas at Arlington">
  $css_main
</head>
);
    if ($show_page eq 's1') {
	print qq(<body onload="document.forms['barcode'].elements['bcs'].focus()">\n);
    } elsif ($show_page eq 's2') {
	print qq(<body onload="document.forms['callNumber'].elements['cns'].focus()">\n);
    } else {
	print qq(<body>\n);
    }
    print qq(
    <div id="topBar">
       <span id="logo">ShelfLister</span>
       <span id="topNav">
         <a $active_search href="$this_script$search_link">$Lang::string_search</a>
         <a $active_help href="$this_script?show=help">$Lang::string_help</a>
       </span>
    </div>
    <div id="mainContent">
    );
}


##########################################################
#  CSS Style Sheets 
##########################################################

sub InternalCSS {
  my $css = qq(
    <style type="text/css">
    <!--
    body {
      margin: 0;
      font-family: sans-serif; 
      max-width: 320px;
    }
    h1 {
      font-size: 1.1em;
      font-weight: bold;
      margin: 4px 5px 9px 10px;
    }
    h1.error {
      color: red;
    }
    p {
      margin-top: 3px; 
    }
    legend {
      border: 2px solid #D8DFEA;
      padding: 0 1em 0 1em;
    }
    fieldset {
      border: 2px solid #D8DFEA;
    }
    #topBar {
      background-color: #3B5998;
      font-weight: bold;
      border-bottom: 2px solid #6D84B4;
      padding: 4px 0px 4px 0px; 
      min-height: 1.2em;
    }
    #logo {
      float: left;
      color: #ffffff;
      font-size: 1.2em;
      margin: 0 15px 0 15px;
      letter-spacing: 1px;
      text-shadow: #222222 0.1em 0.1em 0.2em;
    }
    #topNav {
      margin: 0 7px 0 7px;
      float: right;
    }
    #topNav a, #titleCallNoToggle a {
      background-color: #D8DFEA;
      text-decoration: none;
      color: #000000;
      color: #3B5998;
      border: 2px solid #6D84B4;
      padding: 0 5px 0 5px;
    }
    #titleCallNoToggle a {
      display: block;
    }
    #topNav a.activeMenu {
      background-color: #FFFFFF;
    }
    #titleCallNoToggle {
      font-weight: bold;
      float: right;
    }
    #mainContent {
      margin: 10px 5px 5px 5px; 
      clear: both;
    }
    .margin {
      margin-left: 15px;
    }
    .tabsContainer {
      float: left;
      /*
      */
      margin: 0;
      padding: 0;
    }
    .tabs {
      white-space: nowrap;
      margin-left: 10px;
    }
    ul.tabs {
      list-style-type: none;
      list-style-position: outside;
      margin: 0;
      padding: 0;
    }
    .tabs li {
      display: inline;
      float: left;
      border: 2px solid #D8DFEA;
      padding: 2px 6px 2px 6px;
      margin: 0 4px -2px 6px;
    }
    .tabs a {
      text-decoration: none;
    }
    .tabs a:hover {
      text-decoration: underline;
    }
    .tabs li.on {
      border-bottom: 2px solid #FFFFFF;
    }
    .tabs li.off {
      background-color: #D8DFEA;
    }
    .selected li {
      background-color: #ECEFF5;
    }
    .formOn {
      clear: both;
      border: 2px solid #D8DFEA;
      padding: 7px 7px 7px 7px;
      max-width: 310px;
    }
    input, select {
      font-size: 1em;
      margin-bottom: 5px;
    }
    .formCheckBoxes {
      float: left;
    }
    .formSubmit {
      float: right;
      vertical-align: bottom;
      margin: 2em 15px 0 0;
    }
    .clear {
      clear: both;
    }
    .prevNext {
      text-align: center;
      margin: 5px 20px 5px 20px;
    }
    .prevBtn {
      float: left;
    }
    .nextBtn {
      float: right;
    }
    .fauxButton {
      text-decoration: none;
      background-color:#3B5998;
      color: #FFFFFF;
      font-weight: bold;
      border: 1px outset #000000;
      padding: 2px 3px 2px 3px;
    }
    #shelfListTable {
    }
    table {
      clear: both;
      padding: 0;
      border-collapse: collapse;
      margin-top: 5px;
    }
    th {
      white-space: nowrap;
    }
    tr#shelfList {
      /*
      border-bottom: 2px solid #ECEFF5;
      */
    }
    th#listHeader {
      text-align: left;
      margin-left: 5px;
    }
    tr.recordRow {
      /*
      border-bottom: 1px solid #ECEFF5;
      */
    }
    tr.recordRow a.numLink {
      text-decoration: none;
      border: 2px solid #6D84B4;
      color: #3B5998;
      padding: 0 3px 0 3px;
      white-space: nowrap;
      background-color: #D8DFEA;
    }
    td {
      padding: 2px 2px 0 2px;
    }
    .cnplusToggle a {
      font-weight: bold;
      font-size: 1.1em;
      text-decoration: none;
      background-color: #FFF8C6;
      border: 2px solid #6D84B4;
      padding: 0 4px 0 4px;
      margin-left: 2px;
    }
    .cnplusOn {
      background-color: #FFF8C6;
      padding: 0 3px 0 3px;
      white-space: nowrap;
    }
    #copy {
      clear: both;
      margin-top: 5px;
      margin-left: 20px;
      font-size: 0.8em;
    }
    #copy a {
      text-decoration: none;
    }
    #copy a:hover {
      text-decoration: underline;
    }
    .author {
      margin: 20px;
    }
    .center {
      text-align: center;
    }
    .small {
      font-size: small;
    }
    .itemNum {
      margin: 5px;
      font-weight: bold;
    }
    .itemTitle {
      margin: 5px;
      font-weight: bold;
    }
    .itemStats {
      padding-top: 5px;
      border-top: 1px solid #6D84B4;
    }
    .itemStatus {
    }
    .itemBarcode {
    }
    .data {
      font-weight: bold;
    }
    .topBorder {
      border-top: 1px solid #6D84B4;
    }
    #lookUp {
      margin: 8px 0 0 0;
      padding: 3px;
    }
    #lookUp ul {
      margin: 5px;
    }
    #lookUp li {
      list-style: none;
    }
    #lookUp li a {
    }
  );
  if ($device eq 'iphone') {
      $css .= qq(
    body {
      max-width: 100%;
    }
    #topNav {
      margin-top: 5px;
    }
    #topNav a, #titleCallNoToggle a {
      padding: 7px 7px 7px 7px;
      -webkit-border-radius: 9px;
    }
    .tabs li {
      padding: 4px 10px 4px 10px;
      margin: 0 5px -2px 8px;
      -webkit-border-top-right-radius: 9px;
      -webkit-border-top-left-radius: 9px;
    }
    input, select {
      font-size: 1em;
      margin-bottom: 10px;
    }
    .checkbox {
       width: 25px;
       height: 25px;
    }
    .cnplusToggle a {
      padding: 3px 8px 3px 8px;
      -webkit-border-radius: 9px;
    }
    tr.recordRow a.numLink {
      -webkit-border-radius: 5px;
    }
    .fauxButton {
      padding: 5px 7px 5px 7px;
      -webkit-border-radius: 6px;
    }
    #lookUp ul {
      margin-left: 0;
      margin-right: 0;
      padding-left: 0;
      padding-right: 0;
    }
    #lookUp li {
      padding: 5px 10px 5px 10px;
      margin-bottom: 4px;
      border: 2px solid #6D84B4;
      background-color: #D8DFEA;
      -webkit-border-radius: 6px;
    }
    #lookUp li a {
      display: block;
      font-weight: bold;
      text-decoration: none;
    }
      );
  }
  if ($browser eq 'chrome') {
      $css .= qq(
    #topNav a, #titleCallNoToggle a {
      -webkit-border-radius: 7px;
    }
    .tabs li {
      -webkit-border-top-right-radius: 7px;
      -webkit-border-top-left-radius: 7px;
    }
    .cnplusToggle a {
      -webkit-border-radius: 7px;
    }
    tr.recordRow a.numLink {
      -webkit-border-radius: 7px;
    }
    .fauxButton {
      -webkit-border-radius: 5px;
    }
      );
  }
  if ($Lang::text_direction =~ /RTL/i) {
      $css .= qq(
    html {
      direction: rtl;
    }
    #logo {
      float: right;
    }
    #topNav {
      float: left;
    }
    .english {
      direction: ltr;
    }
    .tabsContainer {
      float: right;
      /* width needed for IE, or tabs disappear to right */
      width: 100%;
    }
    .tabs li {
      float: right;
    }
    .formCheckBoxes {
      float: right;
    }
    .formSubmit {
      float: left;
    }
    #titleCallNoToggle {
      float: left;
    }
    th#listHeader {
      text-align: right;
    }
    .prevBtn {
      float: right;
    }
    .nextBtn {
      float: left;
    }
      );
  }
  $css .= qq(
    -->
    </style>
  );
  return($css);
}

##########################################################
#  PrintTail
##########################################################
#
#  Finishes off the HTML page

sub PrintTail {
    if ($valid eq "T") {
        print qq(
        <div> 
         <a href="http://validator.w3.org/check/referer"><img src="http://rocky.uta.edu/doran/image/checkmark_green_in_square_02.gif" border="0" width="19" height="16" alt="Validate the HTML of this page"></a>
        </div> 
        );
    }
    print qq(
  </div>
</body>
</html>);

    exit (0);
}


##########################################################
#  ShowMIF  
##########################################################
#

sub ShowMIF {
    PrintHead();
    print qq(
      <h1>$Lang::string_help : $Lang::string_mif_file</h1>
    );
    open (SAVEFILE, "<$report_dir/$out_file")
        || ($out_file = "no file yet");

    my ($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$file_size, $atime,
	$mtime,$ctime,$blksize,$blocks) = stat(SAVEFILE);

#  Need to format output if using this stuff...
#    my $file_size_units;
#    if ($file_size >= '1048576') {
#	$file_size = $file_size / 1048576;
#        $file_size_units = "Mbytes";
#    } elsif ($file_size > '1024') {
#	$file_size = $file_size / 1024;
#        $file_size_units = "Kbytes";
#    } else {
#        $file_size_units = "bytes";
#    }
    my $file_size_units = "bytes";

    my $entries     = "";
    my $start_stamp = "";
    my $end_stamp   = "";
    while (my $line = <SAVEFILE>) {
	chomp $line;
	$entries++;
        if ($entries == "1") {
            $start_stamp = $line;
            $start_stamp =~ s/^(.+?)\|.+/$1/;
        }
        $end_stamp = $line;
        $end_stamp =~ s/^(.+?)\|.+/$1/;
    }
    if (! $entries) {
#	$entries = "None";
	$file_size_units = "";
    }

    print qq(
        <div class="english">
	Marked items are saved to a
	file on the server.<br><br>
	<table summary="Marked items file information">
	  <tr>
	    <td align="right">
		Filename:&nbsp;
	    </td>
	    <td>
		$out_file
	    </td>
	  </tr>
	  <tr>
	    <td align="right">
		Size:&nbsp;
	    </td>
	    <td>
		$file_size $file_size_units
	    </td>
	  </tr>
	  <tr>
	    <td align="right">
		Directory:&nbsp;
	    </td>
	    <td>
		$report_dir/
	    </td>
	  </tr>
	  <tr>
	    <td align="right">
		Entries:&nbsp;
	    </td>
	    <td>
		$entries
	    </td>
	  </tr>
	  <tr>
	    <td align="right">
		First:&nbsp;
	    </td>
	    <td>
		$start_stamp
	    </td>
	  </tr>
	  <tr>
	    <td align="right">
		Last:&nbsp;
	    </td>
	    <td>
		$end_stamp
	    </td>
	  </tr>
	</table>
	<br>
	Marking items does <em>not</em> update the Voyager database.  The Marked Items File is a text file containing one line for each marked item.  Fields are: 
  <ul>
    <li>date stamp</li>
    <li>bib ID</li>
    <li>MFHD ID</li>
    <li>item ID</li>
    <li>barcode</li>
    <li>selected "Mark Item" value</li>
    <li>call number</li>
  </ul>
This file can be downloaded and imported into an Access table.  Fields are pipe ("|") delimited.  Barcode data can be extracted into a text file and used for "Pick and Scan."<br><br>Note that entries for books that lack an item record will not include an item ID or barcode value. 
    </div>
    );
    close (SAVEFILE);

    PrintTail();
}


##########################################################
#  ShowHelp  
##########################################################
#

sub ShowHelp {
    my ($topic) = @_;
    if ($topic eq 'copyright') {
        PrintHead("$Lang::string_help : $Lang::string_copyright");
	print qq{
        <h1>$Lang::string_help : $Lang::string_copyright</h1>
  <div class="small english">
   Copyright 2003-2009, The University of Texas at Arlington ("UTA").
   All rights reserved.
  <p>
  By using this software the USER indicates that he or she has read, understood and and will comply with the following:
  </p>
  <p>
  UTA hereby grants USER permission to use, copy, modify, and distribute this software and its documentation for any purpose and without fee, provided that:
  </p>
  <p>
  1. the above copyright notice appears in all copies of the software and its documentation, or portions thereof, and
  </p>
  <p>
  2. a full copy of this notice is included with the software and its documentation, or portions thereof, and
  </p>
  <p>
  3. neither the software nor its documentation, nor portions thereof, is sold for profit.  Any commercial sale or license of this software, copies of the software, its associated documentation and/or modifications of either is strictly prohibited without the prior consent of UTA.
  </p>
  <p>
  Title to copyright to this software and its associated documentation shall at all times remain with UTA.  No right is granted to use in advertising, publicity or otherwise any trademark, service mark, or the name of UTA.
  </p>
  <p>
  This software and any associated documentation are provided "as is," and UTA MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESSED OR IMPLIED, INCLUDING THOSE OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE, OR THAT USE OF THE SOFTWARE, MODIFICATIONS, OR ASSOCIATED DOCUMENTATION WILL NOT INFRINGE ANY PATENTS, COPYRIGHTS, TRADEMARKS OR OTHER INTELLECTUAL PROPERTY RIGHTS OF A THIRD PARTY. UTA, The University of Texas System, its Regents, officers, and employees shall not be liable under any circumstances for any direct, indirect, special, incidental, or consequential damages with respect to any claim by USER or any third party on account of or arising from the use, or inability to use, this software or its associated documentation, even if UTA has been advised of the possibility of those damages.
  </p>
  <p>
  Submit commercialization requests to: The University of Texas at Arlington, Office of Grant and Contract Services, 701 South Nedderman Drive, Box 19145, Arlington, Texas 76019-0145, ATTN: Director of Technology Transfer.
  </p>
  </div>
        };
    } elsif ($topic eq 'about') {
        PrintHead("$Lang::string_help : $Lang::string_about");
	print qq(
        <h1>$Lang::string_help : $Lang::string_about</h1>
        );
        if ($Lang::blurb_about) {
            print qq($Lang::blurb_about);
        } else {
	    print qq(
        <p class="english">
          ShelfLister generates a real-time shelf list from a Voyager integrated library system.
          It is designed to be accessed with a wireless-enabled mobile device. 
        </p>
            );
         }
	print qq(
         <div id="lookUp">
         <ul>
           <li>
             <a href="$this_script?show=help&amp;topic=accessibility">$Lang::string_help_access</a>
           </li>
           <li>
             <a href="$this_script?show=help&amp;topic=copyright">$Lang::string_copyright</a>
           </li>
        </ul>
        </div>
        <p class="author english">
	Michael Doran, Systems Librarian<br>
	University of Texas at Arlington<br>
	doran\@uta.edu<br>
        http://rocky.uta.edu/doran/
        </p>
        );
    } elsif ($topic eq 'accessibility') {
        PrintHead("$Lang::string_help : $Lang::string_help_access");
	print qq(
        <h1>$Lang::string_help : $Lang::string_help_access</h1>
        );
        if ($Lang::blurb_accessibility) {
            print qq($Lang::blurb_accessibility
            <div class="english">);
        } else {
	    print qq(
        <div>
        <p>
          A good-faith effort has been made to comply with the Web Accessibility Initiative (WAI) Web Content Accessibility Guidelines (WCAG). 
        </p>
            );
        }
	print qq(
        <div id="lookUp">
          Validation via:
          <ul>
            <li>
              <a href="http://validator.w3.org/">W3C Markup Validation Service</a>
            </li>
            <li>
              <a href="http://jigsaw.w3.org/css-validator/">W3C CSS Validation Service</a>
            </li>
            <li>
              <a href="http://fae.cita.uiuc.edu/">Functional Accessibility Evaluator</a>
            </li>
            <li>
              <a href="http://www.totalvalidator.com/">Total Validator</a>
            </li>
          </ul>
        </div>
        <div class="center">
          <img height="31" width="88"
               src="http://www.w3.org/Icons/valid-html401-blue" 
               alt="Valid HTML 4.01 Transitional">
          <img height="31" width="88"
               src="http://www.w3.org/Icons/valid-css2-blue" 
               alt="Valid CSS Level 2">
          <img height="32" width="88" 
               src="http://www.w3.org/WAI/wcag1A-blue"
               alt="Level A conformance icon, W3C-WAI Web Content Accessibility Guidelines 1.0">
        </div>
        </div>
        );
    } elsif ($topic eq 'boxes') {
        PrintHead("$Lang::string_help");
	print qq{
        <h1>$Lang::string_help</h1>
	The <b>place holder</b> option displays a box (&quot;<input type="checkbox" />&quot;) beside each entry.  This box can be checked as a reminder of where you are in the list.
        };
    } elsif ($topic eq 'tutorial') {
        PrintHead("$Lang::string_help : $Lang::string_tutorial_link");
	print qq(
<h1>$Lang::string_help : $Lang::string_tutorial_link</h1>
        );
        if ($Lang::blurb_tutorial) {
            print qq($Lang::blurb_tutorial);
        } else {
	    print qq{
<div class="english">
<ol>
  <li>Take an iPhone, PDA or other wireless-enabled mobile computing device into the stacks.
  <li>Grab a book off the shelf and enter its barcode using the barcode entry form.</li>
  <li>Grab another book further down the shelf and enter its barcode.</li>
  <li>Click the "$Lang::string_form_submit" button to generate a shelf list.</li>
  <li>Select from several list display options.</li>
  <li>Get more detailed information on a book by clicking on its list number.</li>
  <li>Mark items as desired.</li>
</ol>
<strong>More details</strong>
        <br><br>
Although there is an alternate call number entry form you should use the barcode entry whenever possible.
        <br><br>
Note that it is only necessary to input the barcodes of two books on either end of a shelf in order to generate a shelf list for all of the items between (and including) those two books.
        <br><br>
The shelf list page will display up to 50 items, with a link to additional pages if necessary.
        <br><br>
From the shelf list page, clicking on an item's list number will take you to an item view page containing more detailed information about the item. 
        <br><br>
From the item view page, it is possible to mark an item by saving data to a marked items file on the server.  
</div>
            };
        }
    } elsif ($topic eq 'statuses') {
        PrintHead("$Lang::string_help : $Lang::string_help_statuses");
	print qq(
	<h1>$Lang::string_help : $Lang::string_help_statuses</h1>
        <div class="english">
	<dl>
	  <dd><strong>B</strong> - At <strong>B</strong>indery</dd>
	  <dd><strong>C</strong> - <strong>C</strong>harged</dd>
	  <dd><strong>D</strong> - <strong>D</strong>ischarged</dd>
	  <dd><strong>H</strong> - On <strong>H</strong>old</dd>
	  <dd><strong>L</strong> - <strong>L</strong>ost</dd>
	  <dd><strong>M</strong> - <strong>M</strong>issing</dd>
	  <dd><strong>O</strong> - <strong>O</strong>ther</dd>
	  <dd><strong>P</strong> - In <strong>P</strong>rocess</dd>
	  <dd><strong>R</strong> - Cat/Circ <strong>R</strong>eview</dd>
	  <dd><strong>T</strong> - In <strong>T</strong>ransit</dd>
	  <dd>[blank] - Not Charged</dd>
	</dl>
	  <p>Some abbreviations represent multiple possible statuses. For example, &quot;C&quot; can represent either Charged, Renewed, or Overdue.  The <strong>Item View</strong> will show exact status information.</p>
        </div>
        );
    } elsif ($topic eq 'display') {
        PrintHead("$Lang::string_help");
	print qq(
	<h1>$Lang::string_help_list_display</h1>
        <p>coming soon!</p>
        );
    } elsif ($topic eq 'random') {
        PrintHead("$Lang::string_help : $Lang::string_help_random_list");
	print qq(
	<h1>$Lang::string_help : $Lang::string_help_random_list</h1>
	<form name="random" action="$this_script" method="get" accept-charset="UTF-8">
        <fieldset>
          <legend>$Lang::string_random_legend</legend>
	    <input type="hidden" name="show" value="random">
          <div class="formCheckBoxes">
	    <input type="checkbox" name="charges" id="charges" value="Y" class="checkbox"><label for="charges">$Lang::string_ch_full</label><br>
	    <input type="checkbox" name="browses" id="browses" value="Y" class="checkbox"><label for="browses">$Lang::string_br_full</label><br>
	    <input type="checkbox" name="status"  id="status" value="Y" class="checkbox"><label for="status">$Lang::string_st_full</label>
          </div>
          <div class="formSubmit">
	    <input type="submit" class="button" value="$Lang::string_form_submit">
          </div>
          <div class="clear">
	    <input type="hidden" name="stpt" value="1">
          </div>
        </fieldset>
        </form>
        );
#    } else {
#	print qq(
#	<b>Error</b><p>No help topic found.  Sorry!</p>
#	);
    } else {
        PrintHead("$Lang::string_help : $Lang::string_help_contents");
	print qq(
        <h1>$Lang::string_help : $Lang::string_help_contents</h1>
        <div id="lookUp">
        <ul>
          <li>
            <a href="$this_script?show=help&amp;topic=about">$Lang::string_about $this_app</a>
          </li>
          <li>
            <a href="$this_script?show=help&amp;topic=tutorial">$Lang::string_tutorial_link</a>
          </li>
          <li>
            <a href="$this_script?show=help&amp;topic=statuses">$Lang::string_help_statuses</a>
          </li>
          <li>
            <a href="$this_script?show=mif">$Lang::string_mif_file</a>
          </li>
          <li>
            <a href="$this_script?show=help&amp;topic=random">$Lang::string_help_random_list</a>
          </li>
        </ul>
        </div>
	);
    }
    PrintTail();
}


##########################################################
#  TestPage  
##########################################################
#

sub TestPage {
    my ($message) = @_;
    PrintHead("$Lang::string_error");
    print qq(
    <div class="margin">
      <h1 class="error">Test</h1>
      <div class="error">$message</div>
      <div><input type="button" value="$Lang::string_back" class="button" onClick="history.go\(-1\);"></div>
    </div>
    );
    PrintTail();
    DisconnectVygrDB();
    exit(1);
}


##########################################################
#  ErrorPage  
##########################################################
#

sub ErrorPage {
    my ($error) = @_;
    PrintHead("$Lang::string_error");
    print qq(
    <div class="margin">
      <h1 class="error">$Lang::string_error</h1>
      <div class="error">$error</div>
      <div><input type="button" value="$Lang::string_back" class="button" onClick="history.go\(-1\);"></div>
    </div>
    );
    PrintTail();
    DisconnectVygrDB();
    exit(1);
}


##########################################################
#  ErrorConfig  
##########################################################
#

sub ErrorConfig {
    my ($type, $error_message, $system_error_message) = @_;
    $error_out_count++;
    if ($ENV{'SERVER_PROTOCOL'} =~ /http/i ) {
        if ($error_out_count < 2) {
            print qq(Content-Type: text/html\n\n);
            print qq(<html><head><title>Error</title></head><body>);
            print qq(<h1>Error</h1>);
        }
        print qq(<h2>$error_message</h2>);
        print qq(<h3>$system_error_message</h3>);
    } else {
        print "Error: $error_message" . "\n";
        print "System message: $system_error_message" . "\n";
    }
    if ($type =~ /fatal/i) {
      exit(2);
    }
}

exit(0);
