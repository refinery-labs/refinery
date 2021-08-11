# Delete Accounts

## Build and Deploy

`npm i`
`sls deploy`
`sls invoke -f deleteAccount -l --log-type Tail --path mock_event.json`

## Free's fancy concurrency hack
This will run with a concurrency of 100 and will close the accounts.

```sh
xargs -P 100 -I % npx sls invoke -f deleteAccount -l --log-type Tail --data '{"email":"%"}' < accounts-to-close.txt | tee debug-account-logs-.txt
```

You'll probably have some failures, for which you can use this to collect info about what failed:
```sh
comm -3 <( sort accounts-to-close.txt ) <( cat debug-account-logs.txt| grep "DELETED ACCOUNT SUCCESS" | cut -c 102- | sort ) > accounts-still-open.txt
```
