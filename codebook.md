# Reddit Data

## Entities

The dataset contains two different Reddit entities:

1. Submissions -- Post that starts a new discussion thread on Reddit.
2. Comments -- Reply on either a submission or another comment.

The submissions can be seen as the root of a tree, with the comments branching out from
it. Identifiers relate comments to both a submission and / or another comment.
Submission identifiers have the format `t3_<nr>`, while comment identifiers have the
format `<t1_<nr>`. Identifiers for Reddit users are formatted as `t2_<nr>`.

## Submissions

|field|type|description|
|---|---|---|
|id|str|Unique identifier for the submission.|
|title|str|Title for the submission.|
|selftext|str|Text of the submission.|
|link_flair_text|str|Category of the submission, often None.|
|num_comments|int|Number of comments posted under the submission.|
|score|int|Submission score (number of up votes).|
|url|str|Permalint to the submission.|
|author_fullname|str|Unique identifier for the author.|
|created|float|Timestamp when submission was created.|
|created_utc|float|Timestamp when submission was created (UTC).|
|edited|mixed|Timestamp when submission was last edited or False.|
|ups|int|Number of up votes.|
|downs|int|Number of down votes.|
|upvote_ratio|float|Ratio between up and down votes.|
|subreddit|str|Name of the subreddit.|
|subreddit_subscribers|int|Number of subscribers to the subreddit.|
|locked|bool|Boolean indicting whether submission was locked (True) or not (False).|
|media|str|Embedded media as either dict or None.|
|secure_media|str|Embedded media as either dict or None.|
|no_follow|bool|Submission has no follow option on (True) or off (False).|
|over_18|bool|Submission contains adult content (True) or not (False).|
|send_replies|bool|Submission has replies on (True) or off  (False).|


## Comments

|field|type|description|
|---|---|---|
|id|str|Unique identifier for the submission.|
|parent_id|Unique identifier for item being commented on.|
|submission_id|Unique identifier for the top level submission.|
|body|str|Text of the comment.|
|author_fullname|str|Unique identifier for the author.|
|created|float|Timestamp when submission was created.|
|created_utc|float|Timestamp when submission was created (UTC).|
|edited|mixed|Timestamp when submission was last editted or False.|
|ups|int|Number of up votes.|
|downs|int|Number of down votes.|
|subreddit|str|Name of the subreddit.|
