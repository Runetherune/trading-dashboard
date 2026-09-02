"""
CENTRAL ACCOUNT CONFIGURATION
================================
Single source of truth for every account the system knows about -- the
leader (generates signals from its own MT5 data feed) and any follower
accounts (replicate the leader's trades at their own position sizing).

Referenced by: account_status.py, copy_trade.py, generate_dashboard.py.
Change a name or add an account HERE ONLY -- nothing else needs editing.

TO ADD A FOLLOWER ACCOUNT:
1. Set up a SEPARATE MT5 terminal installation logged into that account
   (MT5 can only hold one login per running terminal instance).
2. Add a new MCP server connection in Claude Code for it, e.g.:
   claude mcp add metatrader_2 --scope user -- metatrader-mcp-server
     --login <NEW_LOGIN> --password "<PASSWORD>" --server <SERVER>
     --path "<PATH_TO_THAT_TERMINAL>\terminal64.exe" --transport stdio
3. Add an entry below with that mcp_server_name.
4. Update run_scan.bat's prompt to also execute each new signal on the
   follower's MT5 connection, sized via calculate_lot_size() using the
   follower's OWN balance (not the leader's) -- so risk stays correctly
   proportional per account, not a blind copy of lot size.
"""

ACCOUNTS = {
    "rune_copy": {
        "display_name": "Rune Copy#!",
        "role": "follower",
        "mcp_server_name": "metatrader_2",
        "mt5_login": 5055338800,
        "mt5_server": "MetaQuotes-Demo",
        "balance": 25000,
    },

    "leader": {
        "display_name": "Rune Main",  # <-- change this to whatever you want shown
        "role": "leader",
        "mcp_server_name": "metatrader",
        "mt5_login": 5055310793,
        "mt5_server": "MetaQuotes-Demo",
        "balance": 25000,
    },
    # Example follower entry -- copy this pattern when you add one:
    # "follower_1": {
    #     "display_name": "Zero Eval #1",
    #     "role": "follower",
    #     "mcp_server_name": "metatrader_2",
    #     "mt5_login": 0,
    #     "mt5_server": "FundingPips-Live",
    #     "balance": 25000,
    # },
}

LEADER_KEY = next(k for k, v in ACCOUNTS.items() if v["role"] == "leader")
LEADER_NAME = ACCOUNTS[LEADER_KEY]["display_name"]
