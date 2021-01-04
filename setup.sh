#!/bin/bash

echo "Start installing Mention-bot (For internal use of Meliz)"
echo "It requires an environment that can run python3."
read -p "Would you like to start setting up? (Y), Or just run it? (n): " SETUP
SETUP=${SETUP:-Y}

if [[ $SETUP == [Yy] ]]; then
  echo "Installing required packages..."
  sudo apt update
  sudo apt install -y python3-pip

  if [ "$(dpkg -l | awk '/python3/ {print }' | wc -l)" -ge 1 ]; then
    echo "Python3 package found"
  else
    echo "Failed: It seems that the python environment is not ready."
    exit
  fi

  pip3 install -r requirements.txt || (echo "Failed to install packages" && exit)
  PUBLIC_IP=$(curl ipinfo.io/ip)
  python3 mention_bot.py &>/dev/null & SCRIPT_PID=$!
  sleep 2

  echo "Start testing whether the server is accessible from outside..."
  STATUS_RESPONSE=$(curl -s --connect-timeout 5 "http://$PUBLIC_IP:5000/status")
  if [[ "$STATUS_RESPONSE" != "hello" ]]; then
    echo "[FAILED] You should open the port number 5000 to public"
    kill "$SCRIPT_PID"
    exit
  fi
  echo "Done!"

  read -p "1. Create a bot from your slack configuration (https://api.slack.com/apps)" DUMMY
  read -p "Input your App id (e.g. A01J8S1EVQR): " APP_ID
  read -p "2. Visit [Event Subscriptions] configuration (https://api.slack.com/apps/$APP_ID/event-subscriptions?)" DUMMY
  read -p "3. Enable the toggle button to [On]" DUMMY
  read -p "4. Put this url (http://$PUBLIC_IP:5000/incoming) to the [Request URL] field" DUMMY

  echo "5. Add following permissions from [Subscribe to bot events] section"
  echo "message.im"
  echo "message.channels"
  echo "(Optional) message.groups"
  read
  read -p "6. Click [Save changes] button at the bottom of the page" DUMMY
  read -p "7. Visit this page (https://api.slack.com/apps/$APP_ID/oauth?)" DUMMY
  read -p "8. From [Scopes] section, click [Add an OAuth Scope]" DUMMY
  read -p "9. Add [chat:write] permission" DUMMY
  read -p "10. Visit this page (https://api.slack.com/apps/$APP_ID/general?)" DUMMY
  read -p "11. Click [Install your app] and click [Install to Workspace]" DUMMY
  read -p "12. Visit this page (https://api.slack.com/apps/$APP_ID/install-on-team?)" DUMMY
fi

read -p "Input [Bot User OAuth Access Token] (e.g. xoxb-..): " TOKEN
export SLACK_BOT_TOKEN="$TOKEN"
pkill -f "mention-bot"

echo "Now you are ready to use mention-bot"
echo "Note that people who want receive automatic mentions should send DM to the bot like this:"
echo "> subscribe trello hs_lee (<-my trello id)"
echo "> unsubscribe trello hs_lee"
echo "> subscribe zeplin hs_lee"
echo "> unsubscribe zeplin hs_lee"

python3 mention_bot.py &>/dev/null &
echo "Your bot is now running.."

