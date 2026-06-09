import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Each bucket has:
#   - a compiled OR-chain of sub-patterns (word-boundary anchored)
#   - patterns are grouped thematically so the regex stays readable
# ---------------------------------------------------------------------------

_RAW: dict[str, str] = {
    "pricing_and_billing": r"""
        \b(
            pric(e|es|ing|ed)               # price / prices / pricing / priced
          | cost(s|ing)?                    # cost / costs / costing
          | charg(e|es|ed|ing)              # charge variants
          | invoic(e|es|ed|ing)             # invoice variants
          | bill(s|ed|ing)?                 # bill / billed / billing
          | subscri(be|bed|ption|ptions)    # subscribe / subscription
          | refund(s|ed|ing)?               # refund variants
          | payment(s)?                     # payment / payments
          | discount(s|ed)?                 # discount variants
          | coupon(s)?                      # coupon / coupons
          | tier(s)?                        # tier / tiers (pricing tiers)
          | free\s+trial                    # free trial
          | per\s+(month|year|seat|user)    # per month / per year / per seat
          | annual(ly)?                     # annual / annually
          | cancel(s|led|ling|lation)?      # cancel / cancellation
        )\b
    """,

    "technical_support": r"""
        \b(
            bug(s)?                         # bug / bugs
          | error(s)?                       # error / errors
          | crash(es|ed|ing)?               # crash variants
          | broken                          # broken
          | not\s+work(ing)?                # not working
          | fail(s|ed|ing|ure)?             # fail / failure
          | issue(s)?                       # issue / issues
          | problem(s)?                     # problem / problems
          | fix(es|ed|ing)?                 # fix variants
          | debug(ging)?                    # debug / debugging
          | exception(s)?                   # exception / exceptions
          | timeout(s)?                     # timeout / timeouts
          | slow(ness)?                     # slow / slowness
          | latency                         # latency
          | down(time)?                     # down / downtime
          | outage(s)?                      # outage / outages
          | stack\s+trace                   # stack trace
          | 4\d{2}|5\d{2}                  # HTTP 4xx / 5xx codes
        )\b
    """,

    "product_features": r"""
        \b(
            feature(s)?                     # feature / features
          | how\s+(do\s+i|to|can\s+i)       # how do i / how to / how can i
          | does\s+it\s+(support|have|do)   # does it support / have / do
          | can\s+(it|i|we|you)             # can it / can i / can we
          | capabilit(y|ies)                # capability / capabilities
          | functi(on|ons|onality)          # function / functionality
          | work(s|flow)?                   # works / workflow
          | option(s)?                      # option / options
          | setting(s)?                     # setting / settings
          | enable|disable                  # enable / disable
          | configur(e|ed|ation)            # configure / configuration
          | support(s|ed)?                  # supports / supported
        )\b
    """,

    "onboarding_and_setup": r"""
        \b(
            setup|set\s+up                  # setup / set up
          | install(ed|ing|ation)?          # install variants
          | getting\s+started               # getting started
          | first\s+(time|step(s)?)         # first time / first steps
          | onboard(ing)?                   # onboard / onboarding
          | quickstart                      # quickstart
          | deploy(ed|ing|ment)?            # deploy variants
          | init(ial(ize|ization)?)?        # init / initialize
          | creat(e|ing|ed)\s+(account|project|workspace)  # create account etc.
          | sign\s*(up|in)                  # sign up / sign in
          | register(ed|ing)?               # register variants
          | migrat(e|ed|ion|ing)            # migrate / migration
          | import(ed|ing)?                 # import variants
        )\b
    """,

    "security_and_privacy": r"""
        \b(
            password(s)?                    # password / passwords
          | 2fa|mfa|two[\s\-]factor        # 2FA / MFA variants
          | auth(entication|orization)?     # auth / authentication
          | sso|saml|oauth                  # SSO / SAML / OAuth
          | gdpr|ccpa|hipaa                 # compliance acronyms
          | (data\s+)?(breach|leak(ed)?)    # data breach / leak
          | encrypt(ed|ion)?                # encrypt / encryption
          | permission(s)?                  # permission / permissions
          | access\s+(control|level|right)  # access control / level
          | vulnerabilit(y|ies)             # vulnerability / vulnerabilities
          | compli(ant|ance)                # compliant / compliance
          | audit\s+(log|trail)             # audit log / trail
          | token(s)?                       # token / tokens (API tokens)
          | secret(s)?                      # secret / secrets
          | key(s)?\s+(rotation|management) # key rotation / management
        )\b
    """,

    "integrations": r"""
        \b(
            integrat(e|ed|ion|ions|ing)     # integrate / integration
          | api                             # API (common enough standalone)
          | webhook(s)?                     # webhook / webhooks
          | plugin(s)?                      # plugin / plugins
          | connector(s)?                   # connector / connectors
          | connect(ed|ing|ion)?            # connect variants
          | sync(ing|ed|hroniz(e|ation))?   # sync / synchronize
          | zapier|make|n8n                 # popular automation tools
          | slack|teams|jira|salesforce     # common integration targets
          | rest(ful)?|graphql|grpc         # API paradigms
          | sdk(s)?                         # SDK / SDKs
          | third[\s\-]party               # third-party
          | embed(ded|ding)?                # embed / embedded
        )\b
    """,

    "roadmap_and_future": r"""
        \b(
            roadmap                         # roadmap
          | when\s+(will|is|are|can)        # when will / when is
          | plan(ned|s|ning)?               # planned / planning
          | upcoming                        # upcoming
          | future\s+(feature|release|update|version)
          | next\s+(version|release|update|sprint)
          | eta                             # ETA
          | release\s+(date|notes?|schedule)
          | in\s+development                # in development
          | backlog                         # backlog
          | prioriti(ze|zed|zing|ty)        # prioritize / priority
          | Q[1-4]\s*\d{4}                  # Q1 2025 / Q3 2026 etc.
          | v?\d+\.\d+(\.\d+)?              # version numbers v2.1 / 3.0.1
        )\b
    """,
}

# Compile once with VERBOSE + IGNORECASE
PATTERNS: dict[str, re.Pattern] = {
    bucket: re.compile(_RAW[bucket], re.VERBOSE | re.IGNORECASE)
    for bucket in _RAW
}

@dataclass
class RegexResult:
    bucket: str | None
    matched_keywords: list[str]
    all_scores: dict[str, int]     # keyword hit count per bucket

def classify_regex(text: str) -> RegexResult:
    scores: dict[str, int] = {}
    matched_kw: list[str] = []
    for bucket, pattern in PATTERNS.items():
        hits = pattern.findall(text)
        # findall returns tuples when there are groups — flatten to strings
        flat = [h[0] if isinstance(h, tuple) else h for h in hits if h]
        scores[bucket] = len(flat)
        if flat:
            matched_kw.extend(flat)

    best = max(scores, key=lambda b: scores[b])
    return RegexResult(
        bucket=best if scores[best] > 0 else None,
        matched_keywords=matched_kw,
        all_scores=scores,
    )
