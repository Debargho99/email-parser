import re
import email.charset
from pathlib import Path
from glob import glob
from email import message_from_binary_file, policy

RE_QUOPRI_BS = re.compile(r'\b=20=\n')
RE_QUOPRI_LE = re.compile(r'\b=\n')
RE_LONG_WORDS = re.compile(r'\b[\w\/\+\=\n]{72,}\b')

email.charset.ALIASES.update({
    'iso-8859-8-i': 'iso-8859-8',
    'x-mac-cyrillic': 'mac-cyrillic',
    'macintosh': 'mac-roman',
    'windows-874': 'cp874',
    # manually fix unknown charset encoding
    'default': 'utf-8',
    'x-unknown': 'utf-8',
    '%charset': 'utf-8',
})

def extract_body(msg, depth=0):
    """ Extract content body of an email messsage """
    body = []
    if msg.is_multipart():
        main_content = None
        # multi-part emails often have both
        # a text/plain and a text/html part.
        # Use the first `text/plain` part if there is one,
        # otherwise take the first `text/*` part.
        for part in msg.get_payload():
            is_txt = part.get_content_type() == 'text/plain'
            if not main_content or is_txt:
                main_content = extract_body(part)
            if is_txt:
                break
        if main_content:
            body.extend(main_content)
    elif msg.get_content_type().startswith("text/"):
        # Get the messages
        charset = msg.get_param('charset', 'utf-8').lower()
        # update charset aliases
        charset = email.charset.ALIASES.get(charset, charset)
        msg.set_param('charset', charset)
        try:
            body.append(msg.get_content())
        except AssertionError as e:
            print('Parsing failed.    ')
            print(e)
        except LookupError:
            # set all unknown encoding to utf-8
            # then add a header to indicate this might be a spam
            msg.set_param('charset', 'utf-8')
            body.append('=== <UNKOWN ENCODING POSSIBLY SPAM> ===')
            body.append(msg.get_content())
    return body


def read_emails(dirpath):
    """ Read all emails under a directory
    Returns:
      a iterator. Use
          for x in read_emails():
              print(x)
      to access the emails.
    """
    dirpath = os.path.expanduser(dirpath)
    print('%s/data/inmail.*' % dirpath)
    for filename in glob('%s/data/inmail.*' % dirpath):
        print('Read %s' % filename, end='\r')
        msg = message_from_binary_file(open(filename, mode="rb"),
                                       policy=policy.default)
        body = '\n\n'.join(extract_body(msg))
        # remove potential quote print formatting strings
        body = RE_QUOPRI_BS.sub('', body)
        body = RE_QUOPRI_LE.sub('', body)
        body = RE_LONG_WORDS.sub('', body)
        yield {
            "_id": os.path.basename(filename).replace('.', '_'),
            "subject": msg['subject'],
            "text": body or ''
        }

