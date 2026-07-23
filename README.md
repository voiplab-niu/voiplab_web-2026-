# 從github下載Web檔案

## 下載
使用clone指令可以將你的檔案從github下載下來
1. 請在你要的下載的位置使用
````
git clone https://github.com/voiplab-niu/webonline.git
````
:::info
裡面會有個隱藏資料架叫做 `.git`會負責將你github的位置記錄下來
:::

## 上傳
在你有`.git`資料夾的那層使用
````
git config --global user.email "voiplab.niu@gmail.com"
git config --global user.name "voiolab.niu"
````
:::success
以上只有第一次會用到
:::

````
git add .
````
- 將當前目錄下所有已更改的文件（包括新增、修改或刪除的文件）添加到暫存區（Staging Area），準備進行提交。
- . 表示當前目錄及其子目錄下的所有文件。
````
git commit -m "你的提交信息"
````
- 將暫存區中的所有變更提交到本地儲存庫中。
- -m "你的提交信息" 用來為這次提交添加一個簡短的描述（提交信息），描述這次更改的內容。

````
git push
````
- 將本地儲存庫中的最新提交推送到遠程儲存庫（通常是 GitHub、GitLab 等），使遠程儲存庫同步更新。
## 如果已經下過clone指令的電腦
在你有`.git`資料夾的那層使用
````
git pull
````
:::info
`git pull`是由`git fetch`和`git merge`組成

- `git fetch`：
    從遠程儲存庫中抓取最新的更改（但不會自動合併），將其下載到本地儲存庫。
- `git merge`：
    將剛才抓取到的更改合併到當前的本地分支中。
    
因此，執行`git pull`後，你的本地分支將與遠程儲存庫保持同步，並包含最新的更改。
這個命令常用於在你開始新的開發工作之前，確保你的工作基礎是最新的。
:::

