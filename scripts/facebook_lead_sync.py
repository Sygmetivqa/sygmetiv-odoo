#!/usr/bin/env python3
"""Pull Facebook Instant Form leads into Odoo CRM.

The Oracle server calls Meta, then creates the lead on Odoo through localhost.
No inbound port is opened. Python standard library only.

  python3 facebook_lead_sync.py --list-forms
  python3 facebook_lead_sync.py --dry-run
  python3 facebook_lead_sync.py --once
"""

import argparse
import calendar
import configparser
import html
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xmlrpc.client
from pathlib import Path

GRAPH_HOST = "graph.facebook.com"
CONFIG_NAME = "facebook_lead_sync.conf"
STATE_NAME = "facebook_lead_sync.state.json"

NAME_KEYS = ("full_name", "full name")
FIRST_KEYS = ("first_name", "first name")
LAST_KEYS = ("last_name", "last name")
EMAIL_KEYS = ("email", "work_email", "email_address")
PHONE_KEYS = ("phone_number", "phone", "work_phone_number", "mobile_number")
COMPANY_KEYS = ("company_name", "company")


class SyncError(Exception):
    pass


def load_config(path):
    parser = configparser.ConfigParser()
    read = parser.read(path)
    if not read:
        raise SyncError("Config file not found: %s" % path)
    required = {
        "odoo": ("url", "database", "username", "api_key"),
        "facebook": ("graph_version", "page_id", "page_token"),
        "lead": ("title_prefix", "source_line"),
    }
    for section, keys in required.items():
        if not parser.has_section(section):
            raise SyncError("Config is missing the [%s] section." % section)
        for key in keys:
            if not parser.get(section, key, fallback="").strip():
                raise SyncError("Config %s is empty: [%s] %s" % (path, section, key))
    return parser


def graph_get(url):
    host = urllib.parse.urlparse(url).hostname
    if host != GRAPH_HOST:
        raise SyncError("Refused to call a host other than %s." % GRAPH_HOST)
    request = urllib.request.Request(url, headers={"User-Agent": "sygmetiv-facebook-lead-sync"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise SyncError("Meta returned HTTP %s.\n%s" % (error.code, body)) from error
    except urllib.error.URLError as error:
        raise SyncError("Could not reach Meta: %s" % error.reason) from error
    if "error" in payload:
        message = payload["error"].get("message") or payload["error"]
        raise SyncError("Meta error: %s" % message)
    return payload


def graph_url(version, path, token, query=None):
    version = version if version.startswith("v") else "v" + version
    params = dict(query or {})
    params["access_token"] = token
    return "https://%s/%s/%s?%s" % (GRAPH_HOST, version, path.lstrip("/"), urllib.parse.urlencode(params))


def list_forms(config):
    facebook = config["facebook"]
    url = graph_url(facebook["graph_version"], "%s/leadgen_forms" % facebook["page_id"].strip(), facebook["page_token"].strip(), {"limit": 100})
    forms = []
    while url:
        payload = graph_get(url)
        forms.extend(payload.get("data") or [])
        url = (payload.get("paging") or {}).get("next")
    return forms


def fetch_leads(config, since_epoch):
    facebook = config["facebook"]
    form_id = facebook.get("form_id", "").strip()
    if not form_id:
        raise SyncError("Config [facebook] form_id is empty. Run --list-forms and paste the form id.")
    filtering = json.dumps([{"field": "time_created", "operator": "GREATER_THAN", "value": int(since_epoch)}])
    url = graph_url(
        facebook["graph_version"],
        "%s/leads" % form_id,
        facebook["page_token"].strip(),
        {"limit": 100, "filtering": filtering},
    )
    leads = []
    while url:
        payload = graph_get(url)
        leads.extend(payload.get("data") or [])
        url = (payload.get("paging") or {}).get("next")
    leads.sort(key=lambda item: item.get("created_time") or "")
    return leads


def field_map(field_data):
    values = {}
    for item in field_data or []:
        name = str(item.get("name") or "").strip().lower()
        text = ", ".join(str(value).strip() for value in (item.get("values") or []) if str(value).strip())
        if name and text:
            values[name] = text
    return values


def first_of(values, keys):
    for key in keys:
        if values.get(key):
            return values[key]
    return ""


def contact_name(values):
    full = first_of(values, NAME_KEYS)
    if full:
        return full
    joined = " ".join(part for part in (first_of(values, FIRST_KEYS), first_of(values, LAST_KEYS)) if part)
    return joined


def build_lead(values, lead_id, created_time, title_prefix, source_line):
    name = contact_name(values) or "Facebook lead"
    prefix = (title_prefix or "").strip()
    title = "%s %s" % (prefix, name) if prefix else name
    email = first_of(values, EMAIL_KEYS)
    phone = first_of(values, PHONE_KEYS)
    company = first_of(values, COMPANY_KEYS)
    used = set(NAME_KEYS + FIRST_KEYS + LAST_KEYS + EMAIL_KEYS + PHONE_KEYS + COMPANY_KEYS)
    notes = [source_line.strip(), "Facebook lead id: %s" % lead_id]
    if created_time:
        notes.append("Submitted: %s" % created_time)
    if company:
        notes.append("Company: %s" % company)
    for key, text in values.items():
        if key not in used:
            notes.append("%s: %s" % (key.replace("_", " "), text))
    description = "".join("<p>%s</p>" % html.escape(line) for line in notes)
    lead = {
        "name": title,
        "contact_name": name,
        "description": description,
        "type": "lead",
    }
    if email:
        lead["email_from"] = email
    if phone:
        lead["phone"] = phone
    if company:
        lead["partner_name"] = company
    return lead


def odoo_proxy(url, endpoint):
    return xmlrpc.client.ServerProxy("%s/xmlrpc/2/%s" % (url.rstrip("/"), endpoint), allow_none=True)


def connect_odoo(config):
    odoo = config["odoo"]
    url = odoo["url"].strip()
    database = odoo["database"].strip()
    username = odoo["username"].strip()
    api_key = odoo["api_key"].strip()
    try:
        uid = odoo_proxy(url, "common").authenticate(database, username, api_key, {})
    except Exception as error:
        raise SyncError("Odoo login failed: %s" % error) from error
    if not uid:
        raise SyncError("Odoo rejected the database, username, or API key.")
    return database, uid, api_key, odoo_proxy(url, "object")


def find_team_id(models, database, uid, api_key, team_name):
    if not team_name:
        return None
    found = models.execute_kw(database, uid, api_key, "crm.team", "search", [[("name", "=", team_name)]], {"limit": 1})
    if not found:
        raise SyncError("No sales team named %r. Check CRM → Configuration → Sales Teams." % team_name)
    return found[0]


def already_imported(models, database, uid, api_key, lead_id):
    found = models.execute_kw(
        database,
        uid,
        api_key,
        "crm.lead",
        "search",
        [[("description", "like", "Facebook lead id: %s" % lead_id)]],
        {"limit": 1},
    )
    return bool(found)


def load_state(path):
    if not path.exists():
        return {"seen_ids": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"seen_ids": []}


def save_state(path, state):
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def since_epoch(config, state):
    raw = config.get("facebook", "since", fallback="").strip()
    if not raw:
        raise SyncError("Config [facebook] since is empty. Use a date, for example 2026-10-20.")
    try:
        parsed = time.strptime(raw, "%Y-%m-%d")
    except ValueError as error:
        raise SyncError("Config [facebook] since must be YYYY-MM-DD.") from error
    configured = int(calendar.timegm(parsed))
    previous = int(state.get("last_success_epoch") or 0)
    # One day of overlap. The Facebook lead id stops a second copy.
    if previous:
        return max(configured, previous - 86400)
    return configured


class RunLock:
    def __init__(self, path):
        self.path = path
        self.fd = None

    def _holder_is_running(self):
        try:
            pid = int(self.path.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
        except (OSError, ValueError):
            return False
        return True

    def __enter__(self):
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as error:
            if self._holder_is_running():
                raise SyncError("Another sync is still running. Wait for it to finish.") from error
            self.path.unlink()
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(self.fd, str(os.getpid()).encode())
        return self

    def __exit__(self, exc_type, exc, traceback):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        if self.path.exists():
            self.path.unlink()


def run(config, config_path, dry_run):
    state_path = config_path.with_name(STATE_NAME)
    state = load_state(state_path)
    seen = set(str(item) for item in state.get("seen_ids") or [])
    leads = fetch_leads(config, since_epoch(config, state))
    database, uid, api_key, models = connect_odoo(config)
    team_id = find_team_id(models, database, uid, api_key, config.get("lead", "sales_team", fallback="").strip())
    created = 0
    for item in leads:
        lead_id = str(item.get("id") or "").strip()
        if not lead_id or lead_id in seen:
            continue
        if already_imported(models, database, uid, api_key, lead_id):
            seen.add(lead_id)
            continue
        values = build_lead(
            field_map(item.get("field_data")),
            lead_id,
            item.get("created_time") or "",
            config.get("lead", "title_prefix"),
            config.get("lead", "source_line"),
        )
        if team_id:
            values["team_id"] = team_id
        if dry_run:
            print("Would create: %s <%s> %s" % (values["name"], values.get("email_from", ""), values.get("phone", "")))
            continue
        models.execute_kw(database, uid, api_key, "crm.lead", "create", [values])
        seen.add(lead_id)
        created += 1
        print("Created: %s (Facebook lead id %s)" % (values["name"], lead_id))
    if not dry_run:
        state["seen_ids"] = sorted(seen)
        state["last_success_epoch"] = int(time.time())
        save_state(state_path, state)
    print("%s lead(s). Meta returned %s row(s) in this window." % ("Would create" if dry_run else "Created", len(leads)))
    return created


def main(argv):
    parser = argparse.ArgumentParser(description="Pull Facebook Instant Form leads into Odoo CRM.")
    parser.add_argument("--config", default=str(Path(__file__).with_name(CONFIG_NAME)))
    parser.add_argument("--list-forms", action="store_true", help="Print form names and ids for this Page.")
    parser.add_argument("--dry-run", action="store_true", help="Show leads that would be created.")
    parser.add_argument("--once", action="store_true", help="Create new leads, then exit.")
    args = parser.parse_args(argv)
    if not (args.list_forms or args.dry_run or args.once):
        parser.error("Choose --list-forms, --dry-run, or --once.")
    config_path = Path(args.config)
    config = load_config(config_path)
    if args.list_forms:
        forms = list_forms(config)
        if not forms:
            print("Meta returned no Instant Forms for this Page.")
            return 0
        for form in forms:
            print("%s\t%s" % (form.get("id"), form.get("name")))
        return 0
    lock_path = config_path.with_name("facebook_lead_sync.lock")
    with RunLock(lock_path):
        run(config, config_path, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SyncError as error:
        print("Stopped: %s" % error, file=sys.stderr)
        sys.exit(1)
