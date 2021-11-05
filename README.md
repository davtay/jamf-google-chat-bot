[![pylint](https://github.com/davtay/jamf-google-chat-bot/actions/workflows/pylint.yml/badge.svg)](https://github.com/davtay/jamf-google-chat-bot/actions/workflows/pylint.yml)

# Google Chat bot for a growing list of tasks in Jamf Pro.

Current implementation supports slash commands for the following endpoints:

<ul>
    <li>/api/v1/computers-inventory?section=GENERAL&section=HARDWARE&section=OPERATING_SYSTEM&section=STORAGE&page=0&page-size=100&sort=id:asc&filter=hardware.serialNumber=={serial}</li>
    <li>/api/v2/computer-prestages/{id}/scope and /api/v2/computer-prestages/{old_id}/scope/delete-multiple using POST</li>
    <li>/api/v1/computers-inventory/{id} with DELETE</li>
</ul>

Slash Command #1 requires a serial number.  
Slash Command #2 requires a serial number and prestage alias, which is set as envioronment variables.  
Slash Command #3 requires a serial number.
