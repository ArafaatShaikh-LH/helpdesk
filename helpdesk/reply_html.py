from html import escape
from html.parser import HTMLParser


class ReplyHTMLParser(HTMLParser):
    """Prepare reply HTML without building or comparing deeply nested tag trees.

    This is an email transformation, not a sanitizer. Existing sendmail security
    checks remain responsible for sanitizing the outgoing message.
    """

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        self.append_starttag(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self.append_starttag(tag, attrs, self_closing=True)

    def append_starttag(self, tag, attrs, self_closing=False):
        src = dict(attrs).get("src")
        if (
            tag not in ("img", "video")
            or not src
            or not src.startswith(("/private/files/", "/files/"))
        ):
            self.parts.append(self.get_starttag_text())
            return

        # Only local media is embedded by sendmail; external and CID URLs stay intact.
        attributes = []
        for name, value in attrs:
            if name in ("src", "embed"):
                continue
            attributes.append(
                name if value is None else f'{name}="{escape(value, quote=True)}"'
            )
        attributes.append(f'embed="{escape(src, quote=True)}"')
        ending = " />" if self_closing else ">"
        self.parts.append(f"<{tag} {' '.join(attributes)}{ending}")

    def handle_endtag(self, tag):
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")

    def handle_comment(self, data):
        # Outlook conditional comments must not become visible text in plain-text mail.
        pass

    def handle_decl(self, decl):
        self.parts.append(f"<!{decl}>")

    def handle_pi(self, data):
        self.parts.append(f"<?{data}>")

    def unknown_decl(self, data):
        # Drop standalone Outlook conditional markers, like their comment equivalents.
        pass
