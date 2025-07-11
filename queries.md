1. Search across both category fields when someone asks about categories:
- CompanyCategory (company type: Private Limited Company, Charitable, etc.)
- Accounts.AccountCategory (account type: MICRO ENTITY, SMALL, DORMANT, etc.)
2. Handle specific category queries like:
- "private limited companies" → searches CompanyCategory
- "charitable companies" → searches CompanyCategory
- "dormant companies" → searches Accounts.AccountCategory
- "micro entity companies" → searches Accounts.AccountCategory
- "companies with no accounts" → searches Accounts.AccountCategory
3. Show both category fields in results when category-related queries are made. Now you can ask questions like:
- "show me private limited companies"
- "list dormant companies"
- "charitable organizations"
- "companies with full accounts"
- "micro entity companies"
- The system will search the appropriate category field(s) and return relevant results!