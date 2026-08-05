import os
import re
import urllib.parse
import urllib.request

from flask import Flask, request, jsonify, render_template_string, abort

app = Flask(__name__)


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>Voice Agent</title>

    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }

        body {
            background: #000;
            color: #fff;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }

        .container {
            text-align: center;
        }

        h2 {
            font-size: 2.5rem;
            margin-bottom: 40px;
            letter-spacing: 1px;
        }

        button {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: none;
            background: #ffffff;
            color: #000;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: 0.3s;
        }

        button:hover {
            transform: scale(1.08);
            box-shadow: 0 0 25px rgba(255, 255, 255, 0.5);
        }

        button:active {
            transform: scale(0.95);
        }

        #status {
            margin-top: 30px;
            font-size: 18px;
            color: #ccc;
            min-height: 25px;
        }
    </style>
</head>

<body>

    <div class="container">

        <h2>🎤 Voice Agent</h2>

        <button onclick="start()">
            Speak
        </button>

        <p id="status"></p>

    </div>


    <script>

        const SpeechRecognition =
            window.SpeechRecognition ||
            window.webkitSpeechRecognition;

        const statusText =
            document.getElementById("status");


        async function sendCommand(command) {

            try {

                statusText.innerText =
                    "Processing: " + command;


                const response = await fetch("/agent", {

                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        text_command: command
                    })

                });


                const data = await response.json();


                if (!response.ok) {

                    statusText.innerText =
                        data.error || "Something went wrong.";

                    return;
                }


                if (data.error) {

                    statusText.innerText =
                        data.error;

                    return;
                }


                statusText.innerText =
                    "Opening...";


                if (data.url) {

                    window.open(
                        data.url,
                        "_blank"
                    );

                }

            }

            catch (error) {

                console.error(error);

                statusText.innerText =
                    "Unable to connect to the server.";

            }

        }


        function start() {

            if (!SpeechRecognition) {

                alert(
                    "Speech recognition is not supported. Please use Google Chrome or Microsoft Edge."
                );

                return;
            }


            const recognition =
                new SpeechRecognition();


            recognition.lang = "en-US";

            recognition.interimResults = false;

            recognition.continuous = false;


            statusText.innerText =
                "🎤 Listening...";


            recognition.onresult = function(event) {

                const command =
                    event.results[0][0].transcript;


                statusText.innerText =
                    "You said: " + command;


                sendCommand(command);

            };


            recognition.onerror = function(event) {

                console.error(
                    "Speech recognition error:",
                    event.error
                );


                statusText.innerText =
                    "Speech error: " + event.error;

            };


            recognition.onend = function() {

                console.log(
                    "Speech recognition ended."
                );

            };


            try {

                recognition.start();

            }

            catch (error) {

                console.error(error);

                statusText.innerText =
                    "Could not start microphone.";

            }

        }

    </script>

</body>
</html>
"""


def find_first_video_id(query):

    """
    Searches YouTube and attempts to find
    the first video ID.
    """

    try:

        search_url = (
            "https://www.youtube.com/results?search_query="
            + urllib.parse.quote_plus(query)
        )


        request_object = urllib.request.Request(

            search_url,

            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                ),

                "Accept-Language":
                    "en-US,en;q=0.9"
            }

        )


        response = urllib.request.urlopen(
            request_object,
            timeout=10
        )


        html = response.read().decode(
            "utf-8",
            errors="ignore"
        )


        matches = re.findall(
            r'"videoId":"([A-Za-z0-9_-]{11})"',
            html
        )


        if matches:

            return matches[0]


        return None


    except Exception as error:

        print(
            "YouTube search error:",
            error
        )

        return None



def build_youtube_target(command):

    """
    Converts a voice command into
    a YouTube URL.
    """

    command = command.lower().strip()


    play_command = (
        "play" in command
    )


    # Remove common voice phrases

    query = command


    patterns = [

        r"^open\s+youtube\s+and\s+play\s+",

        r"^open\s+youtube\s+and\s+search\s+for\s+",

        r"^open\s+youtube\s+",

        r"^play\s+",

        r"^search\s+for\s+",

        r"^search\s+",

        r"^find\s+"

    ]


    for pattern in patterns:

        query = re.sub(
            pattern,
            "",
            query,
            flags=re.IGNORECASE
        )


    # Remove "on YouTube" from end

    query = re.sub(
        r"\s+on\s+youtube\s*$",
        "",
        query,
        flags=re.IGNORECASE
    )


    query = query.strip()


    # If no query was provided

    if not query:

        return "https://www.youtube.com"


    # If user said PLAY

    if play_command:

        video_id = find_first_video_id(
            query
        )


        if video_id:

            return (
                "https://www.youtube.com/watch?v="
                + video_id
                + "&autoplay=1"
            )


    # Otherwise perform YouTube search

    return (
        "https://www.youtube.com/results?search_query="
        + urllib.parse.quote_plus(query)
    )



def build_gmail_target(command):

    """
    Converts a voice command into
    a Gmail compose URL.

    Examples:

    Send email to john@gmail.com
    Send email to john@gmail.com saying hello

    Send mail to john saying meeting at 5
    """

    command = command.lower().strip()


    recipient = ""

    body = ""


    # Find email recipient

    match = re.search(

        r"\bto\s+"
        r"([a-zA-Z0-9._%+\-]+"
        r"(?:\s+[a-zA-Z0-9._%+\-]+)*"
        r"(?:@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})?)"
        r"(?=\s+(?:and\s+)?"
        r"(?:type|saying|message|that)\b|$)",

        command,

        flags=re.IGNORECASE
    )


    if match:

        recipient = (
            match.group(1)
            .strip()
        )


    # If no domain was provided

    if recipient and "@" not in recipient:

        recipient += "@gmail.com"


    # Find email body

    body_match = re.search(

        r"\b(?:type|saying|message)\s+(.+)$",

        command,

        flags=re.IGNORECASE
    )


    if body_match:

        body = (
            body_match.group(1)
            .strip()
            .capitalize()
        )


    # If no email information exists

    if not recipient and not body:

        return "https://mail.google.com"


    # Gmail compose parameters

    parameters = {

        "view": "cm",

        "fs": "1",

        "to": recipient,

        "body": body

    }


    return (
        "https://mail.google.com/mail/u/0/?"
        + urllib.parse.urlencode(parameters)
    )



@app.route("/")
def home():

    return render_template_string(
        HTML
    )



@app.post("/agent")
def agent():

    data = request.get_json(
        silent=True
    )


    if not data:

        abort(
            400,
            description="Invalid JSON request."
        )


    if "text_command" not in data:

        abort(
            400,
            description="Missing command."
        )


    command = str(
        data["text_command"]
    ).lower().strip()


    if not command:

        return jsonify(
            error="Please say a command."
        ), 400


    # -----------------------------
    # YouTube
    # -----------------------------

    if (
        "youtube" in command
        or "play" in command
        or "search" in command
    ):

        target_url = build_youtube_target(
            command
        )


        return jsonify(

            action="open_tab",

            url=target_url

        )


    # -----------------------------
    # Gmail / Email
    # -----------------------------

    if any(

        keyword in command

        for keyword in [
            "gmail",
            "email",
            "mail"
        ]

    ):

        target_url = build_gmail_target(
            command
        )


        return jsonify(

            action="open_tab",

            url=target_url

        )


    # -----------------------------
    # Unknown command
    # -----------------------------

    return jsonify(

        error=(
            "Sorry, I don't understand "
            "that command yet."
        )

    ), 400



if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            8000
        )
    )


    app.run(

        host="0.0.0.0",

        port=port

    )

