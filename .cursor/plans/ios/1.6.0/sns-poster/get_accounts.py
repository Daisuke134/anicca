#!/usr/bin/env python3
"""
Blotato アカウント情報取得スクリプト
接続されているアカウントの確認用
"""
import json
from blotato import BlotatoClient


def main():
    client = BlotatoClient()
    
    print("=== Blotato Connected Accounts ===\n")
    
    response = client.list_accounts()
    accounts = response.get("items", [])
    
    print(f"Total accounts: {len(accounts)}\n")
    
    for acc in accounts:
        platform = acc.get("platform", "unknown")
        account_id = acc.get("id", "N/A")
        username = acc.get("username", "") or acc.get("fullname", "N/A")
        
        print(f"  {platform.upper()}")
        print(f"    ID: {account_id}")
        print(f"    User: {username}")
        print()
    
    print("=" * 40)
    print("\n📌 Pinterest Board ID 取得方法:")
    print("   1. https://my.blotato.com にアクセス")
    print("   2. Remix画面で Pinterest の投稿を作成")
    print("   3. 「Publish」をクリック")
    print("   4. 表示される Board ID をコピー")
    print("   5. config.py の ACCOUNTS['pinterest']['board_id'] に設定")
    print()


if __name__ == "__main__":
    main()

