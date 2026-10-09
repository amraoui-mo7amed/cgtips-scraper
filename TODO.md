
## Features Implementation

- [x] re-Download all the missing models at one:
    - by article
    - by category 
    - by subcategory 
- [x] Clear the download list 
- [x] Copy the articles files by:
    - Article
    - Category
    - Subcategory
    **Ps:** 
    - let the user choose an exe file from the settings called `client agent` this file will be autocopied with the articles
    - Also the copy process must be for many destinations/disls at the same time
    - the articles will be coppied to `storage` folder
- [x] Upload articles:
    - by articles
    - by category 
    - by subcategory 
    **Ps:** 
    - API link is `https://loftdesign.bilnov.com/`
    - add a section in settings page to allow the admin to specify the details uysed in api request for auth -username/email and password-
- [x] Download from Fshare.vn (when download link is not Google Drive):
    - Multiple download methods:
        - Guest API (direct HTTP session with countdown and CDN redirect stream)
        - Playwright interactive browser automation (DOM policy checkbox bypass, button triggers, timer tracking)
        - yt-dlp CLI engine
        - Browser session cookie & DOM handshake replay
    - Show download link's provider (Google Drive, Fshare, MediaFire, Mega, Dropbox, etc.) across all article views:
        - Explore View model cards
        - Categories & Feeds grid cards
        - Local Library cards
        - Download Queue list items
        - Direct Resolver results and action buttons


