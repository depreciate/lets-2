<?php

//error_reporting(E_ALL);
//ini_set("display_errors", 1);
/// Does server-side checks to ensure a beatmap can be submitted online, and stores gathered beatmap info
/// in the database.
///
/// Arguments:
/// {u} - Username
/// {h} - Password
/// {s} - BeatmapSetId (if available)
/// {b} - BeatmapIds (comma separated list)

/// {z} - Osz2Hash (if available)
///
/// Returns(a list of responses seperated by newline chars):
/// [0] - Response (0 = success, >0 = error code)
/// [1] - BeatmapSetId (if new)
/// [2] - New beatmapIds (comma separated list, up to count required)
/// [3] - Type of submission (1 = full submit, 2 = patch-submit)
/// [4] - Remaining beatmap quota

define('IN_PHPBB', true);

$phpbb_root_path = '../forum/';
$phpEx = substr(strrchr(__FILE__, '.'), 1);
include($phpbb_root_path . 'common.' . $phpEx);
include($phpbb_root_path . 'includes/functions_admin.' . $phpEx);
include($phpbb_root_path . 'includes/message_parser.' . $phpEx);

$haxSubmitEnabled = false;

$dbOnly = true;
require_once("../include.php");
require_once("include.bmsubmit.php");

$username = $_REQUEST['u'];
$password = $_REQUEST['h'];

$userId = checkOsuAuth($username, $password);

if ($userId < 0)
    return_errorcode(5, "Authentication failure.  Please check your login details.");

if ($conn->queryOne("SELECT osu.check_silenced($userId)"))
    return_errorcode(5, "You are unable to submit/update maps while silenced.");

if ($conn->queryOne("SELECT user_warnings FROM phpbb_users WHERE user_id = $userId"))
    return_errorcode(5, "Your account is currently restricted.");

$beatmapSetId = (int) $_REQUEST['s'];
$beatmapIds = explode(',', $_REQUEST['b']);
$oldOsz2Hash = $_REQUEST['z'];

$creatorId = -1;
$approvalStatus;
$newSubmit;
$osz2Available = false;
$bubbled = false;

//delete any inactive maps first...
$inactives = $conn->queryMany("SELECT beatmapset_id FROM osu_beatmapsets WHERE user_id = $userId AND active = -1");
if (count($inactives))
{
    foreach ($inactives as $i)
        $conn->exec("DELETE FROM osu_beatmaps WHERE beatmapset_id = $i AND user_id = $userId");
    $conn->exec("DELETE FROM osu_beatmapsets WHERE user_id = $userId AND active = -1");
}

if ($beatmapSetId > 0 && fetch_info($beatmapSetId, $creatorId, $approvalStatus, $osz2Available))
{
    //if we come here the beatmapset already exists.

    //if(!$osz2Available)
    //	return_errorcode(24, "Can't replace existing non-osz2 beatmaps.");

    //check if beatmapSetID is associated with the submitter.
    if (!authenticate_creator($userId, $creatorId, $username))
        return_errorcode(1, "");

    //if ranked
    if ($approvalStatus > 0 && !has_special_permissions($username))
        return_errorcode(3, "");

    if ($approvalStatus < -1)
        return_errorcode(4, "");

    $bubbled = $conn->queryOne("SELECT icon_id FROM phpbb_topics WHERE topic_id = (SELECT thread_id FROM osu_beatmapsets WHERE beatmapset_id = $beatmapSetId)") == 7;

}
else
{
    $remainingQuota = check_remaining_uploadcap($userId);

    //we create a new beatmapset
    $beatmapSetId = create_beatmapset($userId, $username);
    $newSubmit = true;
}

renew_beatmapids_if_invalid($beatmapIds, $beatmapSetId, $userId);

$serverHash = get_osz2_file_hash($beatmapSetId);

$fullSubmit = $newSubmit || $oldOsz2Hash == "0" || !$serverHash || $serverHash != $oldOsz2Hash;

echo    "0\n" .                             //Success
        "$beatmapSetId\n" .                 //only new if new submission
        implode(",", $beatmapIds) . "\n" .  //beatmapId's (possibly updated) in a comma separated list
        ($fullSubmit ? "1" : "2") . "\n" .  //fullsubmit if it's a new submit or the client has no package to patch from
        $remainingQuota . "\n" .            //remaining beatmap-quota
        ($bubbled ? "1" : "0")  . "\n" .
        $approvalStatus;

function check_remaining_uploadcap($userId)
{
    global $conn;

    //Beatmap upload cap
    $unrankedCount = $conn->queryOne("select count(*) from osu_beatmapsets where approved in (-1,0) and active > 0 and user_id = $userId");
    $rankedCount = $conn->queryOne("select count(*) from osu_beatmapsets where approved > 0 and active > 0 and user_id = $userId");

    //Limits maximum submissions to 2 + min(3,rankedMapCount)
    //or for supporters, a maximum submissions to 3 + min(5,rankedMapCount)

    if ($conn->queryOne("select osu_subscriber from phpbb_users where user_id = $userId") == 1)
        $mapAllowance = 4 + min(6, $rankedCount);
    else
        $mapAllowance = 3 + min(3, $rankedCount);

    if ($unrankedCount + 1 > $mapAllowance)
        return_errorcode(6, "You have exceeded your submission cap (you are currently allowed $mapAllowance total unranked maps)." .
                "Please finish the maps you have currently submitted, or wait until your submissions expire automatically to the graveyarded (~4weeks).");

    return $mapAllowance - $unrankedCount;
}

function create_beatmapset($userId, $username)
{
    global $conn;

    $stmt = $conn->prepare('INSERT INTO osu_beatmapsets (user_id, creator, approved, thread_id, active, submit_date)
                              VALUES (?,?,-1,0,-1,CURRENT_TIMESTAMP)');
    $stmt->bind_param("is", $userId, $username);
    $stmt->execute();
    $stmt->close();
    return $conn->insert_id;
}

//We take each invalid id and replace it by a valid one by querying to the database
function renew_beatmapids_if_invalid(&$beatmapIds, $beatmapSetId, $userId)
{
    global $conn;

    // a beatmapId is declared invalid if the value is:
    // -1, this means the difficulty has never been submitted
    // linked to another beatmapSetId, this means the difficulty is transferred or reused
    // does not exist (anymore)
    $currentBeatmapIds = $conn->queryAll("SELECT beatmap_id FROM osu_beatmaps WHERE beatmapset_id = $beatmapSetId", true);
    $stmt = $conn->prepare("INSERT INTO osu_beatmaps ( user_id, beatmapset_id, approved) VALUES (?,?, -1)");
    foreach ($beatmapIds as &$id)
    {
        if ($id > 0 && in_array(array($id), $currentBeatmapIds))
        {
            //to prevent doubles
            unset($currentBeatmapIds[array_search(array($id), $currentBeatmapIds)]);
            continue;
        }

        $stmt->bind_param("ii", $userId, $beatmapSetId);
        $stmt->execute();
        $id = $conn->insert_id;

    }
    $stmt->close();
    //remove all difficulties that aren't being uploaded but exist on the server
    foreach ($currentBeatmapIds as &$id)
    {
        removeOsuFile($id[0]);
        $conn->exec("DELETE FROM osu_beatmaps where beatmap_id = $id[0]");
    }

    //update difficulty count
    $diffCount = count($beatmapIds);
    $conn->exec("UPDATE osu_beatmapsets SET versions_available = $diffCount where beatmapset_id = $beatmapSetId");
}


?>