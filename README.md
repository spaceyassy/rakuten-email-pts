Prepare following values:
- A: imap server url. e.g. `imap.gmail.com`
- B: folder to parse emails at. e.g. `"Rakuten Point"` (if using filters with labels on gmail)
- C: email address
- D: email password
- E: mark unrelated emails in the same folder as read, `true` or `false`
- F: password on rakuten
- G: email address for Rakuten

Generate the 1-line string
```
IMAP_SERVER='<A>';IMAP_FOLDER='<B>';EMAIL_ADDRESS='<C>';EMAIL_PASSWORD='<D>';EMAIL_MARK_READ='<E>';RAKUTEN_PASSWORD='<F>';RAKUTEN_ADDRESS='<G>'
```
e.g.
```
IMAP_SERVER='imap.gmail.com';IMAP_FOLDER='"Rakuten Point"';EMAIL_ADDRESS='example@gmail.com';EMAIL_PASSWORD='Epassword';EMAIL_MARK_READ='false';RAKUTEN_PASSWORD='Rpassword';RAKUTEN_ADDRESS='example@gmail.com'
```

and paste this string [here](https://opinionatedgeek.com/codecs/base64encoder) to generate a base64 string. If you have multiple accounts, repeat the previous steps and concatenate the resulting base64-encoded strings with a comma: `config1,config2,...`

Next, fork this repo (and star it while you are at it). Go to repository settings -> Secrets and variables -> Actions and add a secret called `CONFIGURATION` with the previously generated string as its value.

GitHub Actions should now run once per day to click on the links.
