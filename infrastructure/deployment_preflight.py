"""Inspect deployment configuration locally without connecting to external services."""

import json
import os
import re
from urllib.parse import urlsplit


def valid_https(endpoint):
    if not isinstance(endpoint, str) or any(char.isspace() for char in endpoint):
        return False
    try:
        url = urlsplit(endpoint)
        return (url.scheme == 'https' and bool(url.hostname) and url.port != 0
                and url.username is None and url.password is None and not url.fragment)
    except ValueError:
        return False


def inspect_configuration(env):
    auth = env.get('FINAGENT_AUTH_MODE', 'demo')
    try:
        sources = json.loads(env.get('FINAGENT_ERP_SOURCES_JSON', '[]'))
    except ValueError:
        sources = None

    if not isinstance(sources, list) or len(sources) > 100:
        erp = 'invalid_registry'
    elif not sources:
        erp = 'not_configured'
    else:
        erp = 'configured_unverified'
        seen = set()
        for source in sources:
            if not isinstance(source, dict):
                erp = 'invalid_registry'
                break
            organization, identifier = source.get('organization_id'), source.get('id')
            if not all(isinstance(value, str) and value.strip()
                       for value in (organization, identifier, source.get('ledger_id'))):
                erp = 'invalid_registry'
                break
            key = organization, identifier
            if key in seen:
                erp = 'duplicate_source'
                break
            seen.add(key)
            if source.get('read_only_verified') is not True:
                erp = 'read_only_attestation_missing'
                break
            kind = source.get('kind', 'rest_json')
            if kind == 'database':
                if not source.get('dsn_env') or not source.get('table') or not source.get('columns'):
                    erp = 'incomplete_database_source'
                    break
            elif kind not in ('rest_json', 'sap_odata', 'oracle_rest', 'kingdee_bill_query') or not valid_https(source.get('url')):
                erp = 'invalid_production_source'
                break
            for field in ('dsn_env', 'headers_env'):
                if field in source:
                    name = source[field]
                    if not isinstance(name, str) or not re.fullmatch(r'FINAGENT_ERP_[A-Z0-9_]+', name) or not env.get(name):
                        erp = 'credential_reference_missing_or_invalid'
                        break
            if erp != 'configured_unverified':
                break

    endpoint = env.get('FINAGENT_ALERT_WEBHOOK')
    webhook = 'not_configured'
    if endpoint:
        webhook = 'configured_unverified' if valid_https(endpoint) else 'invalid_production_endpoint'

    return {
        'authentication': 'users_configured' if auth == 'users' else 'users_required',
        'erp': erp,
        'alert_webhook': webhook,
        'external_acceptance': 'required',
    }


if __name__ == '__main__':
    print(json.dumps(inspect_configuration(os.environ), indent=2))
