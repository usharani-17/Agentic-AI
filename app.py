```python
import os
import re
import urllib.parse
import urllib.request

from flask import Flask, request, jsonify, render_template_string, abort

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
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

#status {
    margin-top: 30px;
    font-size: 18px;
    color: #ccc;
}
</style>
</head>

<body>

<div class="container">
    <h2>🎤 Voice Agent</h2>
    <button onclick="start()">Speak</button>
    <p id="status"></p>
</div>

<script>
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const s = document.getElementById("status");

async function send(cmd) {
    try {
        s.innerText = "Processing: " + cmd;

        const r = await fetch("/agent", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text_command: cmd
            })
        });

        const d = await r.json();

        if (d.error) {
            s.innerText = d.error;
            return;
        }

        s.innerText = "Opening...";

        window.open(d.url, "_blank");

    } catch (error) {
        console.error(error);
        s.innerText = "Something went wrong.";
    }
}

function start() {
    if (!SR) {
        alert("Please use Google Chrome or Microsoft Edge.");
        return;
    }

    const rec = new SR();

    rec.lang = "en-US";
    rec.interimResults = false;
    rec.continuous = false;

    s.innerText = "Listening...";

    rec.onresult = function(e) {
        const command = e.results[0][0].transcript;
        s.innerText = "You said: " + command;
        send(command);
    };

    rec.onerror = function(e) {
        s.innerText = "Error: " + e.error;
    };

    rec.onend = function() {
        console.log("Speech recognition ended.");
    };

    rec.start();
}
</script>

</body>
</html>
"""


def find_first_video_id(query):
    """
    Search YouTube and try to find the first video ID.
    """

    try:
        search_url = (
            "https://www.youtube.com/results?search_query="
            + urllib.parse.quote_plus(query)
        )

        req = urllib.request.Request(
            search_url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-US,en;q=0.9"
            }
        )

        html = urllib.request.urlopen(req, timeout=5).read().decode(
            "utf-8",
            errors="ignore"
        )

        # Find YouTube video IDs
        matches = re.findall(
            r'"videoId":"([A-Za-z0-9_-]{11})"',
            html
        )

        if matches:
            return matches[0]

        return None

    except Exception as e:
        print("YouTube scraper error:", e)
        return None


def build_youtube_target(cmd):
    """
    Convert a voice command into a YouTube URL.
    """

    play = "play" in cmd

    # Remove common voice-command phrases
    q = re.sub(
        r"^(open\s+youtube\s*(and\s*)?(play|search)?|"
        r"play|search\s+for|search|on\s+youtube)\s*",
        "",
        cmd,
        flags=re.IGNORECASE
    ).strip()

    # Remove trailing 'on youtube'
    q = re.sub(
        r"\s+on\s+youtube\s*$",
        "",
        q,
        flags=re.IGNORECASE
    ).strip()

    if not q:
        return "https://www.youtube.com"

    if play:
        video_id = find_first_video_id(q)

        if video_id:
            return (
                f"https://www.youtube.com/watch?v={video_id}"
                "&autoplay=1"
            )

    return (
        "https://www.youtube.com/results?search_query="
        + urllib.parse.quote_plus(q)
    )


def build_gmail_target(cmd):
    """
    Convert a voice command into a Gmail compose URL.

    Examples:
    Send email to john saying hello
    Send mail to john@gmail.com saying meeting at 5
    """

    to = ""
    body = ""

    # Find recipient
    m = re.search(
        r"\bto\s+([a-zA-Z0-9._%+\-]+(?:\s+[a-zA-Z0-9._%+\-]+)*"
        r"(?:@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})?)"
        r"(?=\s+(?:and\s+)?(?:type|saying|message|that)\b|$)",
        cmd,
        flags=re.IGNORECASE
    )

    if m:
        to = m.group(1).strip()

    # If the user didn't provide a domain,
    # assume Gmail.
    if to and "@" not in to:
        to += "@gmail.com"

    # Find email body
    m = re.search(
        r"\b(?:type|saying|message)\s+(.+)$",
        cmd,
        flags=re.IGNORECASE
    )

    if m:
        body = m.group(1).strip().capitalize()

    if not to and not body:
        return "https://mail.google.com"

    params = {
        "view": "cm",
        "fs": "1",
        "to": to,
        "body": body
    }

    return (
        "https://mail.google.com/mail/u/0/?"
        + urllib.parse.urlencode(params)
    )


@app.route("/")
def home():
    return render_template_string(HTML)


@app.post("/agent")
def agent():
    data = request.get_json(silent=True)

    if not data or "text_command" not in data:
        abort(400, description="Missing command")

    cmd = str(data["text_command"]).lower().strip()

    if not cmd:
        return jsonify(error="Please say a command.")

    # YouTube commands
    if "youtube" in cmd or "play" in cmd:
        return jsonify(
            action="open_tab",
            url=build_youtube_target(cmd)
        )

    # Gmail / email commands
    if any(k in cmd for k in ["gmail", "email", "mail"]):
        return jsonify(
            action="open_tab",
            url=build_gmail_target(cmd)
        )

    return jsonify(
        error="Sorry, I don't understand that command yet."
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))

    app.run(
        host="0.0.0.0",
        port=port
    )
```
