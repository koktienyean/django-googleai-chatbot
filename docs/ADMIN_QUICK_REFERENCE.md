# Admin Interface - Quick Reference

**Date**: November 27, 2025
**Purpose**: Quick lookup for common admin tasks

---

## Admin URLs

```
Django Admin Home:      /admin/
Chat Sessions:          /admin/chatbot/chatsession/
Chat Messages:          /admin/chatbot/chat/
Users:                  /admin/auth/user/
```

---

## Chat Sessions Admin

### List Columns
```
[Session Name] [User Link] [Model] [Messages] [Created] [Status Badge]
```

### Quick Filters
```
By Status      → Active / Inactive
By Model       → gemini-2.0-flash / gemini-1.5-flash / gemini-1.5-flash-8b
By Date        → Created date range
By User        → Filter by user
```

### Quick Searches
```
Search by: Session name, Username, User email
```

### Detail View Sections
```
1. Session Information
   - name
   - model
   - is_active

2. User Association
   - user (link)
   - user_info (read-only)

3. Statistics (collapsible)
   - message_count (read-only)
   - created_at (read-only)
   - updated_at (read-only)
```

---

## Chat Messages Admin

### List Columns
```
[Message Preview] [Session Link] [User Link] [Created] [Status Badge]
```

### Quick Filters
```
By Status      → Active / Deleted
By User        → Filter by message owner
By Session     → Filter by session
By Date        → Created date range
```

### Quick Searches
```
Search by: Message text, Response text, Session name, Username
```

### Detail View Sections
```
1. Message Content
   - message
   - response

2. Session Details
   - session (link)
   - session_info (read-only)
   - user_info (read-only)

3. Message Status
   - is_deleted
   - created_at (read-only)

4. Statistics (collapsible)
   - message_length (read-only)
   - response_length (read-only)
```

### Restrictions
```
Cannot create messages:  has_add_permission = False
Cannot hard delete:      has_delete_permission = False
Can soft delete:         Mark is_deleted = True
```

---

## Common Tasks - Quick Steps

### Find All Messages from User "john_doe"

```
1. Click: Admin → Chat Messages
2. Filter: "By User" → Select "john_doe"
3. See: All messages from that user
```

### Find Conversation About "Django"

```
1. Click: Admin → Chat Messages
2. Search: Type "Django"
3. See: Messages and responses mentioning Django
```

### Check Which User Owns Message #42

```
1. Click: Admin → Chat Messages
2. Click: Message #42
3. Look: "User Info" field
4. Shows: username (email) with link
```

### See All Sessions for User

```
1. Click: Admin → Chat Sessions
2. Filter: "By User" → Select user
3. See: All sessions belonging to that user
```

### Count Messages in a Session

```
1. Click: Admin → Chat Sessions
2. Look: "Messages" column
3. Number shows active messages only
4. Click session for more details
```

### Find Messages from Specific Date

```
1. Click: Admin → Chat Messages
2. Click: Date hierarchy at top
3. Navigate: Year → Month → Day
4. See: Messages from that date
```

### View Deleted Messages

```
1. Click: Admin → Chat Messages
2. Filter: "By Status" → Select "Deleted"
3. See: All soft-deleted messages
4. Their user info still visible
```

### Jump from Message to User Admin

```
1. Click: Admin → Chat Messages
2. Click: Any message
3. Click: "User" link in list or detail
4. Jumps: To user admin page
```

### Jump from Message to Session

```
1. Click: Admin → Chat Messages
2. Click: Any message
3. Click: "Session" link
4. Jumps: To session detail page
```

---

## Column Explanation

### Chat Sessions List

| Column | Means |
|--------|-------|
| **Name** | Session title |
| **User** | Who owns it (blue link) |
| **Model** | AI model used |
| **Messages** | Active message count |
| **Created** | When created |
| **Status** | Active (green) / Inactive (red) |

### Chat Messages List

| Column | Means |
|--------|-------|
| **Message** | First 50 chars of user input |
| **Session** | Which session (blue link) |
| **User** | Session owner (blue link) |
| **Created** | When created |
| **Status** | Active (green) / Deleted (red) |

---

## Filter Legend

### By Status (Messages)
```
Active   → is_deleted = False (normal messages)
Deleted  → is_deleted = True (soft deleted)
```

### By Status (Sessions)
```
Active   → is_active = True
Inactive → is_active = False
```

### By User
```
Shows only items belonging to selected user
```

### By Model (Sessions)
```
Shows sessions using specific AI model
```

### By Date
```
Click year/month/day to narrow down results
```

---

## Read-Only Fields

**Cannot Edit** (Read-Only):
```
ChatSession:
- created_at
- updated_at
- message_count (auto-calculated)
- user_info (display only)

Chat:
- created_at
- session_info (display only)
- user_info (display only)
- message_length (auto-calculated)
- response_length (auto-calculated)
```

**Can Edit**:
```
ChatSession:
- name
- model
- user
- is_active

Chat:
- message
- response
- session
- is_deleted
```

---

## Database Query Optimization

```
ChatSessionAdmin uses:
  qs.select_related('user')
  → Fetches user with session in ONE query

ChatAdmin uses:
  qs.select_related('session', 'session__user')
  → Fetches session AND user in efficient queries
```

**Result**: Fast admin load times, no N+1 query problems

---

## Permissions

### Who Can Access?

```
Admin Users (is_staff=True):
  - View all sessions
  - View all messages
  - Edit sessions
  - Soft delete messages
  - Cannot create messages
  - Cannot hard delete messages
```

### What They Can/Cannot Do?

```
ChatSession:
  Create?  → YES (can add sessions)
  Edit?    → YES (can update all fields)
  Delete?  → YES (can soft delete)
  Hard Delete? → YES

Chat Messages:
  Create?  → NO  (prevented by has_add_permission)
  Edit?    → YES (can edit all except timestamps)
  Delete?  → NO  (prevented by has_delete_permission)
  Soft Delete? → YES (via is_deleted field)
```

---

## Useful Django Admin Tricks

### Date Hierarchy Navigation
```
Click date column header to drill down:
  Year → Month → Day
Good for finding messages from specific dates
```

### Column Sorting
```
Click column header to sort by that column
Click again to reverse sort
Check "admin_order_field" for efficient sorts
```

### Search Tips
```
Multi-field search in:
  - Message content
  - Response content
  - Session name
  - Username
Case-insensitive, partial matches work
```

### Batch Actions
```
Check boxes next to items
Use dropdown to perform batch actions
(No delete allowed for data safety)
```

### Related Links
```
Blue text = clickable links
Jump between:
  Message → Session
  Message → User
  Session → User
Maintains filters and context
```

---

## Troubleshooting

### Problem: User field is empty
**Solution**: Check session.user relationship exists

### Problem: Message count is wrong
**Solution**: Count only includes is_deleted=False messages

### Problem: Can't delete a message
**Solution**: This is intentional! Use is_deleted flag instead

### Problem: Can't create message
**Solution**: Messages created by chatbot app, not admin

### Problem: Search not finding anything
**Solution**: Searches are case-insensitive; try simpler keywords

### Problem: Page loading slowly
**Solution**: Use filters/search to limit results instead of viewing all

---

## Admin Interface Sections

### Left Sidebar (Navigation)
```
Chatbot
  ├─ Chat Sessions
  └─ Chat Messages
Authentication and Authorization
  ├─ Groups
  └─ Users
```

### Right Sidebar (Filters)
```
Changes list filters
- By Status
- By User
- By Model (Sessions only)
- By Date
```

### Top Bar (Search)
```
Search box for full-text search
Searches configured fields
Results highlighted in list
```

### Date Hierarchy (Top)
```
Navigate by: Year → Month → Day
Click to filter by date range
Useful for finding recent activity
```

---

## Key Features Summary

✅ **Two Model Admins**: ChatSession + Chat
✅ **User Association**: Every message shows which user owns it
✅ **Quick Filters**: Filter by status, user, model, date
✅ **Smart Search**: Search message content and metadata
✅ **Organized Fields**: Fieldsets group related data
✅ **Color Badges**: Visual status indicators
✅ **Linked Navigation**: Click to jump between related objects
✅ **Performance**: Optimized queries, select_related
✅ **Security**: Soft delete, no manual message creation
✅ **Data Integrity**: Read-only timestamps and counts

---

*Quick Reference - November 27, 2025*
