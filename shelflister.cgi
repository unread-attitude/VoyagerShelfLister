#!/m1/shared/bin/perl

########################################################################
#
#  ShelfLister
#
#  Version: 3.0 for tablets, optimized for iPads
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
#  Copyright 2003-2012, The University of Texas at Arlington ("UTA").
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

use strict;

unless (eval "use CGI") {
    ErrorConfig("fatal", "Missing Perl module", "$@") if $@;
}

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
#  -- ShelfLister.ini
#  -- ShelfLister.English
use lib '../../newbooks';
use lib '../../shelflister';

# Read in base configuration file
#require "ShelfLister.ini";
unless (eval qq(require "ShelfLister.ini")) {
    ErrorConfig("fatal", "Couldn't load required config file", "$@");
} 

# These are currently only used for development
my $css_file     = 'ipad.css';
my $css_file_rtl = 'ipad-rtl.css';

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
#  by copying the ShelfLister.cgi script and giving it a
#  different name.  The "marked items" file will be given
#  the same name, but with a ".txt" file extension.

my $out_file     = fileparse("$this_script", qr/\.[^.]*/) . ".txt";

#  Another alternative is just to hardcode the output filename
#my $out_file     = "shelflister.inp";

#  Application name and version number

my $this_app      = "ShelfLister";
#my $this_app_link = qq(<a href="$this_script?show=s1\&$ENV{'QUERY_STRING'}">$this_app</a>);
my $this_app_link = qq(<a href="$this_script">$this_app</a>);
my $version       = "3.0";


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


#my $doc_type_def = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
#            "http://www.w3.org/TR/html4/loose.dtd">';

my $doc_type_def = '<!DOCTYPE HTML>';

my $query = new CGI;

##########################################################
#  Assign form data to variables.
##########################################################

# Language of user interface
my $language            = decode_utf8($query->param('lang'));

LoadLanguageModule($language);

my $back_button = '';

if ($ShelfListerIni::back_button eq "Y") {
    $back_button = qq(<input type="button" data-icon="arrow-l" data-inline="true" value="$Lang::string_back" onClick="history.go\(-1\);">);
}

my @save_stati;
if (@Lang::save_stati) {
    @save_stati = @Lang::save_stati;
} else {
    @save_stati = @ShelfListerIni::save_stati;
}
 
my $list_display        = '';
$list_display           = decode_utf8($query->param('mode'));
if (! $list_display) {
    $list_display        = $ShelfListerIni::list_display_default;
}

my $mouse_over          = decode_utf8($query->param('omoo'));

# Input from Search Form 1 - Barcode entry

my $barcode_start       = decode_utf8($query->param('bcs'));
my $barcode_end         = decode_utf8($query->param('bce'));

# Input from Search Form 2 - Call Number entry

my $location_id         = decode_utf8($query->param('loc_id'));
my $call_num_start      = decode_utf8($query->param('cns'));
my $call_num_end        = decode_utf8($query->param('cne'));
my $classification      = decode_utf8($query->param('class_type'));
unless ($classification) {
    $classification     = 'LC';
}

# Input from both Search Forms

my $search_type         = decode_utf8($query->param('search'));
my $show_boxes          = decode_utf8($query->param('boxes'));
my $starting_pnt        = decode_utf8($query->param('stpt'));

# Formerly Search Forms input; now ini file config

my $show_charge_stats   = decode_utf8($ShelfListerIni::charges);
my $show_browse_stats  	= decode_utf8($ShelfListerIni::browses);
my $show_item_status    = decode_utf8($ShelfListerIni::status);

my $show_callno_plus    = decode_utf8($query->param('cnplus'));
if ($show_callno_plus ne 'Y' && $show_callno_plus ne 'N') {
    $show_callno_plus    = decode_utf8($ShelfListerIni::cnplus);
}

$starting_pnt =~ s/\D//g;

# Input from Random Test 
my $random_item_id      = $query->param('itemid');

#  Browser detection
#  This part could use some more work.

my $device              = '';
my $user_agent          = $ENV{'HTTP_USER_AGENT'};
my $recs_per_page       = $ShelfListerIni::recs_per_page;

my $ending_pnt          = $starting_pnt + $recs_per_page - 1;

# Input for Item View

my $record_type         = decode_utf8($query->param('record_type'));
my $record_number       = decode_utf8($query->param('record_no'));

# Input for misc. views

my $topic               = decode_utf8($query->param('topic'));
my $show_page           = decode_utf8($query->param('show'));
my @checked_records     = decode_utf8($query->param('check'));

# De-dup and sort the list of checked records
# (Legacy code, not currently used in ShelfLister.)
if (@checked_records) {
    my @uniq;
    my %seen = ();
    foreach my $i (@checked_records) {
        push (@uniq, $i) unless $seen{$i}++;
    }
    @checked_records = (sort { $a <=> $b } @uniq);
}

# Input for saving to file

my $save_action              = decode_utf8($query->param('save_action'));
my $save_status              = decode_utf8($query->param('save_status'));
my $save_bib_id              = decode_utf8($query->param('save_bib_id'));
my $save_mfhd_id             = decode_utf8($query->param('save_mfhd_id'));
my $save_item_id             = decode_utf8($query->param('save_item_id'));
my $save_barcode             = decode_utf8($query->param('save_barcode'));
my $save_call_no             = decode_utf8($query->param('save_call_no'));

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
        $s1_tab     = qq(<a data-role="button" href="$this_script?show=s1">$Lang::string_bc_legend</a>);
        $s2_tab     = qq(<span data-role="button" class="ui-btn-active">$Lang::string_callno_legend</span>);
    } else {
        $s1_tab     = qq(<span data-role="button" class="ui-btn-active">$Lang::string_bc_legend</span>);
        $s2_tab     = qq(<a data-role="button" href="$this_script?show=s2">$Lang::string_callno_legend</a>);
    }
# $s2_tab     = qq(<li><a class="ui-btn-active" href="$this_script?show=s2">$Lang::string_callno_legend</a></li>);

    ConnectVygrDB();

    my $location_field = 'location_name';

    if ($ShelfListerIni::location_name_option eq 'F') {
        $location_field = 'location_display_name';
    }

    # Prepare the first prelimary SQL statement
    my $sth = $dbh->prepare("select location_id, $location_field from $db_name.location where suppress_in_opac not in 'Y' and $location_field is not null and mfhd_count > 1") 
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

    PrintHead("$Lang::string_search_h1");

    print qq(
      <h2>$Lang::string_search_h1</h2>

      <div data-role="controlgroup" data-type="horizontal" class="center">
          $s1_tab$s2_tab
      </div>
    );

    if ($form eq "s1") {
        print encode_utf8(qq(
      <div>
	<form name="barcode" action="$this_script" method="get" accept-charset="UTF-8">
          <div>
	    <input type="hidden" name="search" value="s1">
          </div>

          <div data-role="fieldcontain">
            <label for="bcStart">$Lang::string_bc_start</label>
            <input id="bcStart" type="search" name="bcs" value="" size="20" autofocus>
          </div>

          <div data-role="fieldcontain">
            <label for="bcEnd">$Lang::string_bc_end</label>
            <input id="bcEnd" type="search" name="bce" value="" size="20">
          </div>

          <div class="center">
	    <input type="submit" class="button" data-inline="true" value="$Lang::string_form_submit">
          </div>
          <div>
	    <input type="hidden" name="stpt" value="1">
            $hidden_inputs
          </div>
	</form>
      </div>
        ));
    }
    if ($form eq "s2") {
        print encode_utf8(qq(
      <div>
	<form name="callNumber" action="$this_script" method="get" accept-charset="UTF-8">
	    <input type="hidden" name="search" value="s2">
        ));
        print encode_utf8(qq(
          <div data-role="fieldcontain">
            <label for="loc_id">$Lang::string_callno_location</label>
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

          <div data-role="fieldcontain">
            <label for="callnoStart">$Lang::string_callno_start</label>
            <input type="search" id="callnoStart" name="cns" value="" size="20" autofocus>
          </div>

          <div data-role="fieldcontain">
            <label for="callnoEnd">$Lang::string_callno_end</label>
            <input type="search" id="callnoEnd" name="cne" value="" size="20">
          </div>

          <div data-role="fieldcontain">
            <fieldset data-role="controlgroup">
            <legend>$Lang::string_callno_class</legend>
        ));
           # <label for="callnoClass">$Lang::string_callno_class</label>
        my $checked_radio = '';
        if ($classification eq 'LC') {
            $checked_radio = 'checked="checked"';
        }
        print encode_utf8(qq(
	    <input title="callnoClass" type="radio" name="class_type" $checked_radio value="LC" id="radio-lc" /><label for="radio-lc">$Lang::string_lib_of_congress</label>
        ));
        $checked_radio = '';
        if ($classification eq 'DD') {
            $checked_radio = 'checked="checked"';
        }
        print encode_utf8(qq(
	    <input title="callnoClass" type="radio" name="class_type" $checked_radio value="DD" id="radio-dd" /><label for="radio-dd">$Lang::string_dewey_decimal</label>
        ));
        print encode_utf8(qq(
            </fieldset>
          </div>
          <div class="center">
	    <input type="submit" class="button" data-inline="true" value="$Lang::string_form_submit">
          </div>
          <div class="clear">
	    <input type="hidden" name="stpt" value="1">
            $hidden_inputs
          </div>
	</form>
      </div>
        ));
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
#  NormalizeDewey
##########################################################

sub NormalizeDewey {
    my ($dewey_call_no_orig) = @_;
    my $error_message = "Unparsable call number:";
    my ($dewey_number,
        $everything_else,
        $dewey_call_no,
        $normalized);

    # Remove any initial whitespace
    $dewey_call_no = $dewey_call_no_orig;
    $dewey_call_no =~ s/^\s+//g;
    # Convert all alpha to uppercase
    $dewey_call_no = uc($dewey_call_no);
    if ($dewey_call_no =~ /^\D*([0-9]{3}\.*[0-9]*)\s*(.*)$/) {
        $dewey_number = $1;
        $everything_else = $2;
        # Put a space between any adjoining digit and non-digit
        $everything_else =~ s/(\d)(\D)/$1 $2/g;
        $everything_else =~ s/(\D)(\d)/$1 $2/g;
        # Put a space between any adjoining punctuation and alphanumeric character
        $everything_else =~ s/(\p{P})(\w)/$1 $2/g;
        $everything_else =~ s/(\w)(\p{P})/$1 $2/g;
        # Exception is apparently periods in front of digits
        $everything_else =~ s/(\.) (\d)/$1$2/g;
        # Remove periods not preceding a digit
        $everything_else =~ s/ \. //g;
        # Allow no more than one space in row
        $everything_else =~ s/\s{2,}/ /g;
        # Remove any initial whitespace
        $everything_else =~ s/^\s+//g;
        # Remove any trailing whitespace and periods
        $everything_else =~ s/[\s\.]+$//;
        $normalized = "$dewey_number"
                    . " $everything_else";
        return "$normalized";
    } else {
	ErrorPage("<p>$Lang::string_cn_error</p><p>$dewey_call_no_orig</p>");
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
    if ($classification eq 'LC') {
        $call_num_start = NormalizeLC($call_num_start);
        $call_num_end   = NormalizeLC($call_num_end);
    } elsif ($classification eq 'DD') {
        $call_num_start = NormalizeDewey($call_num_start);
        $call_num_end   = NormalizeDewey($call_num_end);
    } else {
        ErrorPage("$Lang::string_callno_class");
    }

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
    );

    if ($show_charge_stats eq "Y") {
        $table_heading .= qq(
          <th scope="col" class="rightbottom"><abbr title="$Lang::string_ch_full">$Lang::string_ch_abbrev</abbr></th>
        );
    }
    if ($show_browse_stats eq "Y") {
        $table_heading .= qq(
          <th scope="col" class="rightbottom"><abbr title="$Lang::string_br_full">$Lang::string_br_abbrev</abbr></th>
        );
    }

    if ($show_item_status eq "Y") {
        $table_heading .= qq(
          <th scope="col" class="centerbottom"><abbr title="$Lang::string_st_full">$Lang::string_st_abbrev</abbr></th>
        );
    }
#    if ($show_boxes eq "Y") {
#	$table_heading .= qq(
#        <th scope="col">&nbsp;</th>
#        );
#    }
    # check mark &#x2713; checked box &#x22A0;
    $table_heading .= qq(\n          <th scope="col" class="centerbottom">&#x2713;&nbsp;</th>\n);

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
        $callno_plus_toggle_url =~ s/\&cnplus=Y//;
        $callno_plus_toggle_url .= '&cnplus=N';
        $callno_plus_toggle_url =~ s/\&/&amp;/g;
        $call_number_plus_toggle = qq(<span data-role="button"><a href="$callno_plus_toggle_url" class="cnplusToggle" title="$Lang::string_callno_plus_tog">&#x2212; $Lang::string_item_data</a></span>);
    } elsif ($show_callno_plus eq "N") {
        $callno_plus_toggle_url =~ s/\&cnplus=N//;
        $callno_plus_toggle_url .= '&cnplus=Y';
        $callno_plus_toggle_url      =~ s/&omoo=[YN]//;;
        $callno_plus_toggle_url =~ s/\&/&amp;/g;
        $call_number_plus_toggle = qq(<span data-role="button"><a href="$callno_plus_toggle_url" title="$Lang::string_callno_plus_tog">&#x2B; $Lang::string_item_data</a></span>);
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
          <th scope="col" id="listHeader"><span data-role="controlgroup" data-type="horizontal"><span data-role="button"><a class="" href="$switch_mode_link" title="$Lang::string_call_no_blurb">$Lang::string_call_no</a></span><span data-role="button" class="ui-btn-active">$Lang::string_titles</span></span</th>
        </tr>
        );
        # mdd toggle
        $title_callno_toggle_btn = qq(<a href="$switch_mode_link" title="$Lang::string_call_no_blurb">$Lang::string_call_no</a>);
    } else {
        if ($switch_mode_link =~ /mode=1/) {
            $switch_mode_link =~ s/mode=1/mode=2/g;
        } else {
            $switch_mode_link .= '&mode=2';
        }
        $switch_mode_link =~ s/\&/&amp;/g;;

        $table_heading .= qq(
          <th scope="col" id="listHeader"><span data-role="controlgroup" data-type="horizontal"><span data-role="button" class="ui-btn-active">$Lang::string_call_no</span>$call_number_plus_toggle<span data-role="button"><a href="$switch_mode_link" title="$Lang::string_titles_blurb">$Lang::string_titles</a></span></span></th>
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

    if ($ShelfListerIni::location_name_option eq 'F') {
        $location_display = $location_display_name;
    }

    print encode_utf8(qq(
    <h2>$Lang::string_shelf_list</h2>
    <div id="shelvingLocation">
    $Lang::string_location <span class="bold">$location_display</span>
    </div>
    <form>
    <table>
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
    $prev_next = qq(<fieldset class="ui-grid-a">\n);
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
        $prev_next .= qq(<div class="ui-block-a"><a data-role="button" data-icon="arrow-l" data-iconpos="left" href="$this_script?$query_string">$Lang::string_prev</a></div>);
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
	$prev_next .= qq(<div class="ui-block-b"><a data-role="button" data-icon="arrow-r" data-iconpos="right" href="$this_script?$query_string">$Lang::string_next</a></div>);
    }
    $prev_next .= qq(\n  </fieldset>);

    if ($prev_next) {
        print qq($prev_next);
    }
    if ($true_count < 1 ) {
        my $message .= qq(
         <div>
           <h2 class="error">$Lang::string_no_results</h2>
            <p>$Lang::string_no_results_desc</p>
         );
	if ($search_type eq 's2') {
	    $message .= qq(<p>$Lang::string_no_results_loc</p>);
        }
        $message .= qq(
           <div>
             <input type="button" data-icon="arrow-l" data-inline="true" value="$Lang::string_back" class="button" onClick="history.go\(-1\);"></div>
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
      $back_button
      <h2>$Lang::string_item_view</h2>
    );
    my ($call_number, 
        $title, 
        $author, 
        $edition, 
        $bib_id, 
        $mfhd_id, 
        $isbn, 
        $network_no, 
        $oclc_no);
    while( my (@entry) = $sth->fetchrow_array() ) {
	$call_number    = decode_utf8($entry[0]);
	$title 	        = decode_utf8($entry[1]);
	$author         = decode_utf8($entry[2]);
	$edition        = decode_utf8($entry[3]);
	$bib_id         = decode_utf8($entry[4]);
	$mfhd_id        = decode_utf8($entry[5]);
	$isbn           = decode_utf8($entry[6]);
	$network_no     = decode_utf8($entry[7]);
    }

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
         <div class="itemTitle">$title &nbsp; $edition</div>
         <div class="message">$Lang::string_no_item_record</div>
    ));

    # Note: should really use "pass by reference" to pass the %barcode
    # array to subroutine, but this syntax seems to work in this case.
    PrintSaveForm($bib_id, $mfhd_id, "", $call_number, "");

    print encode_utf8(qq(
         <div>
           <ul data-role="listview" data-inset="true">
             <li data-role="list-divider">
                $Lang::string_look_up_in
             </li>
             <li>
               <a href="$ShelfListerIni::webvoyage_server_link$bib_id" target="catalog">$Lang::voyager_record_link_text</a>
             </li>
    ));

    $isbn    = MungeISBN($isbn);
    $oclc_no = MungeNetworkNumber($network_no);

    my $worldcat_link_url = '';
    if ($isbn && $ShelfListerIni::worldcat_link) {
        $worldcat_link_url = $ShelfListerIni::worldcat_link . "/isbn/$isbn";
    } elsif ($oclc_no && $ShelfListerIni::worldcat_link) {
        $worldcat_link_url = $ShelfListerIni::worldcat_link . "/oclc/$oclc_no";
    }
    if ($isbn || $oclc_no) {
        if ($ShelfListerIni::worldcat_link_location) {
            $worldcat_link_url .= "&amp;loc=" . $ShelfListerIni::worldcat_link_location;
            print qq(
             <li>
               <a href="$worldcat_link_url" target="worldcat">$Lang::worldcat_record_link_text</a>
             </li>
            );
        }
    }

    my $google_link_url = '';
    if ($isbn && $ShelfListerIni::google_link) {
        $google_link_url = $ShelfListerIni::google_link . "ISBN$isbn";
    } elsif ($oclc_no && $ShelfListerIni::google_link) {
        $google_link_url = $ShelfListerIni::google_link . "OCLC:$oclc_no";
    }
    if ($isbn || $oclc_no) {
        print qq(
             <li>
               <a href="$google_link_url" target="google">$Lang::google_record_link_text</a>
             </li>
        );
    }
    print qq(
           </ul>
    );

    if ($call_number && $ShelfListerIni::webvoyage_callno_browse) {
        $call_number =~ tr/ /+/;
        $call_number =~ s/([^A-Za-z0-9+])/sprintf("%%%02X", ord($1))/seg;
        print qq(
         <div>
           <ul data-role="listview" data-inset="true">
             <li data-role="list-divider">
                $Lang::string_callno_label
             </li>
             <li>
               <a href="$ShelfListerIni::webvoyage_callno_browse$call_number" target="catalog">$Lang::string_callno_browse</a>
             </li>
           </ul>
         </div>
        );
    }

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
#  MungeNetworkNumber
##########################################################

sub MungeNetworkNumber {
    my ($network_no) = @_;
    if ($network_no =~ /OCoLC/) {
        $network_no =~ s/\s//;
        $network_no =~ s/^[\D]*([\d]*)$/$1/;
        if ($network_no =~ /^[\d]*$/){
            if (length($network_no) > 3 && length($network_no) < 14) {
                return($network_no);
            }
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
      $back_button
      <h2>$Lang::string_item_view</h2>
    );
    my ($call_number,
	$call_number_base,
	$enum,
	$chron,
	$year,
	$copy_number,
	$title,
	$author,
	$edition,
	%status,
	%barcode,
	$bib_id,
	$mfhd_id,
	$item_id,
	$item_type_name,
	$isbn,
	$network_no,
	$hist_charges,
	$hist_browses,
	$item_note,
	$oclc_no);

    while( my (@entry) = $sth->fetchrow_array() ) {
	$call_number 	= decode_utf8($entry[0]);
	$enum	 	= decode_utf8($entry[1]);
	$chron	 	= decode_utf8($entry[2]);
	$year	 	= decode_utf8($entry[3]);
	$copy_number 	= decode_utf8($entry[4]);
	$title 		= decode_utf8($entry[5]);
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
        $network_no     = decode_utf8($entry[20]);
    }
    $call_number_base = $call_number;
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

    # This adds Unicode LRM (LEFT-TO-RIGHT MARK) after ASCII only text
    if ($Lang::text_direction =~ /RTL/i) {
        unless ($title !~ /[\x20-\x7E]/) {
            $title .= "&#x200E;";
            if ($edition) {
                unless ($edition !~ /[\x20-\x7E]/) {
                    $edition .= "&#x200E;";
                }
            }
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

    # Note: Should really use "pass by reference" to pass the %barcode
    # array to subroutine, but this syntax seems to work in this case.
    PrintSaveForm($bib_id, $mfhd_id, $item_id, $call_number, %barcode);

    print qq(
         <div>
           <ul data-role="listview" data-inset="true">
             <li data-role="list-divider">
                $Lang::string_look_up_in
             </li>
             <li>
               <a href="$ShelfListerIni::webvoyage_server_link$bib_id" target="catalog">$Lang::voyager_record_link_text</a>
             </li>
    );

    $isbn    = MungeISBN($isbn);
    $oclc_no = MungeNetworkNumber($network_no);

    my $worldcat_link_url = '';
    if ($isbn && $ShelfListerIni::worldcat_link) {
        $worldcat_link_url = $ShelfListerIni::worldcat_link . "/isbn/$isbn";
    } elsif ($oclc_no && $ShelfListerIni::worldcat_link) {
        $worldcat_link_url = $ShelfListerIni::worldcat_link . "/oclc/$oclc_no";
    }
    if ($isbn || $oclc_no) {
        if ($ShelfListerIni::worldcat_link_location) {
            $worldcat_link_url .= "&amp;loc=" . $ShelfListerIni::worldcat_link_location;
            print qq(
             <li>
               <a href="$worldcat_link_url" target="worldcat">$Lang::worldcat_record_link_text</a>
             </li>
            );
        }
    }

    my $google_link_url = '';
    if ($isbn && $ShelfListerIni::google_link) {
        $google_link_url = $ShelfListerIni::google_link . "ISBN$isbn";
    } elsif ($oclc_no && $ShelfListerIni::google_link) {
        $google_link_url = $ShelfListerIni::google_link . "OCLC:$oclc_no";
    }
    if ($isbn || $oclc_no) {
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

    if ($call_number_base && $ShelfListerIni::webvoyage_callno_browse) {
        $call_number_base =~ tr/ /+/;
        $call_number_base =~ s/([^A-Za-z0-9+])/sprintf("%%%02X", ord($1))/seg;
        print qq(
         <div>
           <ul data-role="listview" data-inset="true">
             <li data-role="list-divider">
                $Lang::string_callno_label
             </li>
             <li>
               <a href="$ShelfListerIni::webvoyage_callno_browse$call_number_base" target="catalog">$Lang::string_callno_browse</a>
             </li>
           </ul>
         </div>
        );
    }

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
        <div data-role="fieldcontain">
        <form action="$this_script" method="get" accept-charset="UTF-8">
          <label for="save_status">$Lang::string_mark_status_label</label>
	  <select name="save_status" size="1" id="save_status">
    );
    foreach my $i (@save_stati) { 
	print "<option>$i</option>\n\t";
    }
    print qq(
	  </select>
	  <input type="submit" name="submit" data-inline="true" value="$Lang::string_mark_submit">
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
	</form>
        </div>\n);
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
    print qq(<p>Marking an item does not update the Voyager database.  It adds an entry to the <a href="$this_script?show=mif">Marked Items File</a>.</p>
    $back_button);
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

    # Ugly hack for getting a proper border using RTL on IE
    if ($Lang::text_direction =~ /RTL/i) {
        $line_number = "&#x200B;" . $line_number . "&#x200B;";
    }
    print qq(\n\t    <tr class="recordRow">);
#    print qq(\n\t<td class="righttop">$line_number</td>);
    if ($show_charge_stats eq "Y") {
        print qq(\n\t      <td class="righttop">);
        print "$hist_charges";
        print "</td>";
    }
    if ($show_browse_stats eq "Y") {
        print qq(\n\t      <td class="righttop">);
        print "$hist_browses";
        print "</td>";
    }
    if ($show_item_status eq "Y") {
        print qq(\n\t      <td class="centertop">);
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

    print qq(\n\t      <td><div class="checkbox"><input type="checkbox" title="Check box" name="check" value="null"></div></td>
    );

    if ($item_id) {
	print encode_utf8(qq(      <td data-role="button" data-corners="false" data-icon="arrow-r" data-iconpos="right" data-mini="true"><a class="listLineLink" href="$this_script?record_type=item&amp;record_no=$item_id">));
    } else {
	print encode_utf8(qq(      <td data-role="button" data-corners="false" data-icon="arrow-r" data-iconpos="right" data-mini="true"><a class="listLineLink" href="$this_script?record_type=mfhd&amp;record_no=$mfhd_id">));
    }

    if ($list_display eq '2') {
        if ($mouse_over eq "Y") {
            print encode_utf8(qq(<span class="listLine" onMouseOver="this.firstChild.nodeValue='$display_call_no';" onMouseOut="this.firstChild.nodeValue='$title_brief';">$title_brief</span>));
        } else {
            print encode_utf8(qq(<span class="listLine">$title_brief</span>));
        }
    } else {
        if ($mouse_over eq "Y") {
            print encode_utf8(qq(<span class="listLine" onMouseOver="this.firstChild.nodeValue='$title_brief';" onMouseOut="this.firstChild.nodeValue='$display_call_no';">$display_call_no</span> $extra_item_info));
        } else {
            print encode_utf8(qq(<span class="listLine">$display_call_no</span> $extra_item_info ));
        }
    }
    print qq(</a></td>\n\t    </tr>);
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
        item_note.item_note,
	bib_text.network_number
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
	bib_text.isbn,
	bib_text.network_number
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

    my $jqm_overrides = q|
      <script>
        $(document).bind("mobileinit", function(){
          //apply jQuery Mobile overrides here
          //e.g. change this for multilingual -mdd
          $.mobile.loadingMessage = "Loading";
        });
      </script>
    |;

    # my $css_main = qq(<link rel="stylesheet" href="$ShelfListerIni::css_directory/$css_file" />);
    my $css_main = InternalCSS();
    if ($Lang::text_direction =~ /RTL/i) {
        $css_main .= qq(<link rel="stylesheet" href="$ShelfListerIni::css_directory/$css_file_rtl" />);
    }
    print "Content-type: text/html; charset=utf-8\n\n";
    print qq( 
$doc_type_def
<html lang="$Lang::language_code">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="format-detection"   content="telephone=no">
  <link rel="apple-touch-icon" sizes="72x72" href="./touch-icon-ipad-72.png" />
  <title>$this_app : $sub_title</title>
  <meta name="dcterms.title"      content="$this_app $version" />
  <meta name="dcterms.creator"    content="Michael Doran" />
  <meta name="dcterms.type"       content="Software" />
  <meta name="dcterms.source"     content="http://rocky.uta.edu/doran/shelflister/" />
  <meta name="dcterms.publisher"  content="University of Texas at Arlington Library" /> 
  <meta name="dcterms.rights"     content="Copyright 2003-2012 University of Texas at Arlington" />
  <link rel="stylesheet" href="http://code.jquery.com/mobile/1.0/jquery.mobile-1.0.min.css" />
  <script src="http://code.jquery.com/jquery-1.6.4.min.js"></script>
  $jqm_overrides
  <script src="http://code.jquery.com/mobile/1.0.1/jquery.mobile-1.0.1.min.js"></script>
  $css_main
</head>
);
    if ($show_page eq 's1') {
	print qq(<body>\n);
    } elsif ($show_page eq 's2') {
	print qq(<body>\n);
    } else {
	print qq(<body>\n);
    }
    print qq(
  <div data-role="page">
    <div data-role="header" data-theme="b">
      <a $active_search data-icon="home" href="$this_script$search_link">$Lang::string_search</a>
      <h1>ShelfLister</h1>
      <a $active_help data-icon="info" href="$this_script?show=help">$Lang::string_help</a>
    </div>
    <div data-role="content">
    );
}

##########################################################
#  CSS Style Sheets
##########################################################

sub InternalCSS {
  my $css = qq(
  <style type="text/css">
  <!--
    /*
    #  This CSS supplements and/or customizes the CSS
    #  provided by the JQuery Mobile framework
    */
h2.error {
  color: red;
}
table {
  font-size: 1.25em;
  width: 100%;
  clear: both;
  padding: 0;
  margin-top: 5px;
  border-collapse: collapse;
}
tr.recordRow {
  border-left: 1px solid #BBBBBB;
}
tr.recordRow:nth-child(2n) {
  border-bottom: 1px solid #BBBBBB;
}
tr.recordRow:last-child {
  border-bottom: 1px solid #BBBBBB;
}
.recordRow .ui-btn {
  margin: 0;
  text-align: left;
}
.recordRow .ui-shadow {
  box-shadow: none;
}
.recordRow:nth-child(odd) .ui-btn {
  border-top: 0;
}
.recordRow:nth-child(2n) .ui-btn {
  border-top: 0;
  border-bottom: 0;
}
.recordRow .ui-btn-inner {
  padding: 0.2em 25px;
  white-space: normal;
}
th {
  white-space: nowrap;
  padding: 3px 7px 3px 7px;
  margin: 10px 20px 10px 20px;
}
th#listHeader {
  text-align: left;
  margin-left: 5px;
}
th.rightbottom {
  text-align: right;
  vertical-align: bottom;
}
th.centerbottom {
  text-align: center;
  vertical-align: bottom;
}
td {
  padding: 6px 7px 0 7px;
}
td.right {
  text-align: right;
}
td.righttop, th.righttop {
  text-align: right;
}
td.centertop, th.centertop {
  text-align: center;
}
td a {
  display:block;
  width:100%;
  height:100%;
  text-decoration:none;
}
.itemNum, .itemTitle {
  font-size: 1.25em;
  font-weight: bold;
  margin-bottom: 5px;
}
.itemTitle {
  font-size: 1.25em;
  font-weight: bold;
}
.itemStats {
  padding-top: 5px;
  border-top: 1px solid #6D84B4;
}
.data {
  font-weight: bold;
}
.recordRow .ui-checkbox {
  margin-bottom: 0;
}
.checkbox {
  text-align: center;
}
.checkbox input {
  width: 2em;
  height: 2em;
  position: static;
}
.cnplusToggle {
  border: 2px solid yellow;
  padding: 2px 6px 2px 6px;
}
.cnplusOn {
  border: 2px solid yellow;
  padding: 0 3px 0 3px;
  white-space: nowrap;
}
#listHeader div.ui-controlgroup {
  margin: 0;
}
#listHeader span.ui-btn-inner {
  padding: 5px 20px;
}
#listHeader a {
  text-decoration: none;
}
#shelfList th {
  border-bottom: 1px solid #BBBBBB;
}
#shelvingLocation {
  margin-left: 0px;
  margin-bottom: 10px;
}
.author {
  margin: 20px;
}
.footertext {
  font-size: 0.75em;
  text-align: center;
}
.bold {
  font-weight: bold;
}
.center {
  text-align: center;
}
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
  <div data-role="footer" data-theme="b">
    <div class="footertext">Copyright 2003-2012 University of Texas at Arlington</div>
  </div>
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
      $back_button
      <h2>$Lang::string_help : $Lang::string_mif_file</h2>
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
	<table>
	  <tr>
	    <td class="right">
		Filename:&nbsp;
	    </td>
	    <td>
		$out_file
	    </td>
	  </tr>
	  <tr>
	    <td class="right">
		Size:&nbsp;
	    </td>
	    <td>
		$file_size $file_size_units
	    </td>
	  </tr>
	  <tr>
	    <td class="right">
		Directory:&nbsp;
	    </td>
	    <td>
		$report_dir/
	    </td>
	  </tr>
	  <tr>
	    <td class="right">
		Entries:&nbsp;
	    </td>
	    <td>
		$entries
	    </td>
	  </tr>
	  <tr>
	    <td class="right">
		First:&nbsp;
	    </td>
	    <td>
		$start_stamp
	    </td>
	  </tr>
	  <tr>
	    <td class="right">
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
        $back_button
        <h2>$Lang::string_help : $Lang::string_copyright</h2>
  <div class="english">
   Copyright 2003-2012, The University of Texas at Arlington ("UTA").
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
        $back_button
        <h2>$Lang::string_help : $Lang::string_about</h2>
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
         <div>
         <ul data-role="listview" data-inset="true">
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
        $back_button
        <h2>$Lang::string_help : $Lang::string_help_access</h2>
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
          <ul data-role="listview" data-inset="true">
            <li data-role="list-divider">
              Validation via:
            </li>
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
        );
    } elsif ($topic eq 'boxes') {
        PrintHead("$Lang::string_help");
	print qq{
        <h2>$Lang::string_help</h2>
	The <b>place holder</b> option displays a box (&quot;<input type="checkbox" />&quot;) beside each entry.  This box can be checked as a reminder of where you are in the list.
        };
    } elsif ($topic eq 'tutorial') {
        PrintHead("$Lang::string_help : $Lang::string_tutorial_link");
	print qq(
        $back_button
<h2>$Lang::string_help : $Lang::string_tutorial_link</h2>
        );
        if ($Lang::blurb_tutorial) {
            print qq($Lang::blurb_tutorial);
        } else {
	    print qq{
<div class="english">
<ol>
  <li>Take an iPad, or other wireless-enabled mobile computing device into the stacks.
  <li>Grab a book off the shelf and enter its barcode using the barcode entry form.</li>
  <li>Grab another book further down the shelf and enter its barcode.</li>
  <li>Click the "$Lang::string_form_submit" button to generate a shelf list.</li>
  <li>Get more detailed information on a book by clicking on the call number/title.</li>
  <li>Mark items as desired.</li>
</ol>
<strong>More details</strong>
        <br><br>
Although there is an alternate call number entry form you should use the barcode entry whenever possible.
        <br><br>
Note that it is only necessary to input the barcodes of two books on either end of a shelf in order to generate a shelf list for all of the items between (and including) those two books.
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
        $back_button
	<h2>$Lang::string_help : $Lang::string_help_statuses</h2>
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
	<h2>$Lang::string_help_list_display</h2>
        <p>coming soon!</p>
        );
    } elsif ($topic eq 'random') {
        PrintHead("$Lang::string_help : $Lang::string_help_random_list");
        my $random_string = CreateRandomString();
	print qq(
        $back_button
	<h2>$Lang::string_help : $Lang::string_help_random_list</h2>
	<form name="random" action="$this_script" method="get" accept-charset="UTF-8">
        <fieldset>
          <legend>$Lang::string_random_legend</legend>
	    <input type="hidden" name="show" value="random">
	    <input type="hidden" name="random_string" value="$random_string">
          <div>
	    <input type="submit" class="button" data-inline="true" value="$Lang::string_form_submit">
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
        <h2>$Lang::string_help : $Lang::string_help_contents</h2>
        <div>
        <ul data-role="listview" data-inset="true">
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
#  CreateRandomString
##########################################################
#
#  Creates a random alpha-numeric ASCII string  

sub CreateRandomString {
  my @alphanumeric_chars = ("A".."Z","a".."z",0..9);
  my $random_string = join("", 
    @alphanumeric_chars[ map {rand @alphanumeric_chars } (1..8) ]);
  return($random_string)
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
      <h2 class="error">Test</h2>
      <div class="error">$message</div>
      <div><input type="button" data-icon="arrow-l" data-inline="true" value="$Lang::string_back" class="button" onClick="history.go\(-1\);"></div>
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
    <div>
      <h2 class="error">$Lang::string_error</h2>
      <div class="error">$error</div>
      <div><input type="button" data-icon="arrow-l" data-inline="true" value="$Lang::string_back" class="button" onClick="history.go\(-1\);"></div>
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
