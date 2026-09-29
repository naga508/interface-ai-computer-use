from flask import Flask, render_template, request

app = Flask(__name__)

MEMBERS = {
    "12345": {
        "name": "Alice Johnson",
        "checking_balance": 1250.10,
        "savings_balance": 8420.37,
    },
    "67890": {
        "name": "Robert Smith",
        "checking_balance": 801.22,
        "savings_balance": 4932.17,
    },
    "55555": {
        "name": "Charlie Davis",
        "checking_balance": 950.25,
        "savings_balance": 6100.50,
    },
}


@app.route("/")
def home():
    return render_template("search.html")


@app.route("/member", methods=["POST"])
def member():
    member_id = request.form.get("member_id", "").strip()
    member_data = MEMBERS.get(member_id)

    if member_data is None:
        return render_template(
            "search.html",
            error="No member found",
        )

    if member_id == "55555":
        return render_template(
            "loading.html",
            member_id=member_id,
        )

    return render_template(
        "member.html",
        member_id=member_id,
        member=member_data,
    )

@app.route("/member/final")
def member_final():
    member_id = request.args.get("member_id", "")
    member_data = MEMBERS.get(member_id)

    if member_data is None:
        return render_template(
            "search.html",
            error="No member found",
        )

    return render_template(
        "member.html",
        member_id=member_id,
        member=member_data,
    )


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
