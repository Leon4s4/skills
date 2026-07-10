# SwiftUI Component Patterns — Apple-Quality

## Table of Contents
- [List & Row Patterns](#list--row-patterns)
- [Form Patterns](#form-patterns)
- [Card Patterns](#card-patterns)
- [Media Components](#media-components)
- [Toolbar & Action Patterns](#toolbar--action-patterns)
- [Search](#search)
- [Pull to Refresh](#pull-to-refresh)
- [Confirmation & Deletion](#confirmation--deletion)
- [Scroll Behaviors](#scroll-behaviors)
- [Section Headers](#section-headers)

---

## List & Row Patterns

### Standard Row with Chevron
```swift
struct ItemRow: View {
    let item: Item

    var body: some View {
        NavigationLink(value: item) {
            HStack(spacing: 12) {
                AsyncImageView(url: item.thumbnailURL)
                    .frame(width: 48, height: 48)
                    .clipShape(.rect(cornerRadius: 8))

                VStack(alignment: .leading, spacing: 2) {
                    Text(item.title)
                        .font(.body)
                        .foregroundStyle(.primary)
                        .lineLimit(1)
                    Text(item.subtitle)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }

                Spacer()
            }
            .contentShape(.rect) // Expand tap area to full row
        }
    }
}
```

### Row with Trailing Metadata
```swift
HStack {
    Label(item.title, systemImage: "star")
    Spacer()
    Text(item.date.formatted(.relative(presentation: .named)))
        .font(.subheadline)
        .foregroundStyle(.secondary)
}
```

### Grouped Sections
```swift
List {
    Section("Recent") {
        ForEach(recentItems) { ItemRow(item: $0) }
    }
    Section("Older") {
        ForEach(olderItems) { ItemRow(item: $0) }
    }
}
.listStyle(.insetGrouped)
```

**Rules:**
- Use `.insetGrouped` for settings/form-like lists
- Use `.plain` for data-driven feeds
- Always use `Section` with headers when grouping related items

---

## Form Patterns

### Standard Settings Form
```swift
Form {
    Section("Profile") {
        TextField("Name", text: $name)
            .textContentType(.name)

        DatePicker("Birthday", selection: $birthday, displayedComponents: .date)

        Picker("Theme", selection: $theme) {
            ForEach(Theme.allCases) { theme in
                Text(theme.displayName).tag(theme)
            }
        }
    }

    Section("Notifications") {
        Toggle("Daily Reminder", isOn: $dailyReminder)
        Toggle("Milestones", isOn: $milestoneAlerts)
    }

    Section {
        Button("Sign Out", role: .destructive) {
            showSignOutConfirmation = true
        }
    }
}
.formStyle(.grouped)
```

### Inline Validation
```swift
TextField("Email", text: $email)
    .textContentType(.emailAddress)
    .keyboardType(.emailAddress)
    .autocapitalization(.none)
    .overlay(alignment: .trailing) {
        if !email.isEmpty {
            Image(systemName: isValidEmail ? "checkmark.circle.fill" : "xmark.circle.fill")
                .foregroundStyle(isValidEmail ? .green : .red)
                .padding(.trailing, 8)
        }
    }

if !email.isEmpty && !isValidEmail {
    Text("Enter a valid email address")
        .font(.caption)
        .foregroundStyle(.red)
}
```

---

## Card Patterns

### Content Card (Feed Item)
```swift
struct MemoryCard: View {
    let memory: Memory

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            HStack(spacing: 10) {
                ProfileImage(url: memory.babyProfile.photoURL, size: 36)
                VStack(alignment: .leading, spacing: 1) {
                    Text(memory.babyProfile.name)
                        .font(.subheadline.weight(.semibold))
                    Text(memory.date.formatted(.relative(presentation: .named)))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Menu {
                    Button("Edit", systemImage: "pencil") { /* ... */ }
                    Button("Share", systemImage: "square.and.arrow.up") { /* ... */ }
                    Divider()
                    Button("Delete", systemImage: "trash", role: .destructive) { /* ... */ }
                } label: {
                    Image(systemName: "ellipsis")
                        .frame(width: 44, height: 44) // Touch target
                        .contentShape(.rect)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)

            // Media
            if let photo = memory.primaryPhoto {
                AsyncImage(url: photo.url) { image in
                    image.resizable().scaledToFill()
                } placeholder: {
                    Rectangle()
                        .fill(.quaternary)
                        .overlay(ProgressView())
                }
                .frame(maxWidth: .infinity)
                .frame(height: 300)
                .clipped()
            }

            // Body
            VStack(alignment: .leading, spacing: 8) {
                Text(memory.text)
                    .font(.body)
                    .lineLimit(3)

                if memory.location != nil {
                    Label(memory.locationName, systemImage: "location")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(16)
        }
    }
}
```

---

## Media Components

### Async Image with Placeholder
```swift
struct ProfileImage: View {
    let url: URL?
    let size: CGFloat

    var body: some View {
        AsyncImage(url: url) { phase in
            switch phase {
            case .success(let image):
                image.resizable().scaledToFill()
            case .failure:
                Image(systemName: "person.crop.circle.fill")
                    .resizable()
                    .foregroundStyle(.quaternary)
            default:
                Circle().fill(.quaternary)
                    .overlay(ProgressView().controlSize(.small))
            }
        }
        .frame(width: size, height: size)
        .clipShape(.circle)
    }
}
```

### Photo Picker Integration
```swift
PhotosPicker(selection: $selectedItem, matching: .images) {
    Label("Choose Photo", systemImage: "photo.on.rectangle")
}
.photosPickerStyle(.inline)             // Embedded picker
.photosPickerDisabledCapabilities(.selectionActions)
```

### Video Thumbnail
```swift
struct VideoThumbnail: View {
    let url: URL

    var body: some View {
        ZStack {
            AsyncImage(url: thumbnailURL) { image in
                image.resizable().scaledToFill()
            } placeholder: {
                Rectangle().fill(.quaternary)
            }

            Circle()
                .fill(.ultraThinMaterial)
                .frame(width: 48, height: 48)
                .overlay {
                    Image(systemName: "play.fill")
                        .font(.title3)
                        .foregroundStyle(.white)
                        .offset(x: 2) // Optical centering
                }
        }
    }
}
```

---

## Toolbar & Action Patterns

### Standard Toolbar
```swift
.toolbar {
    ToolbarItem(placement: .primaryAction) {
        Button("Add", systemImage: "plus") { showAdd = true }
    }
    ToolbarItem(placement: .topBarLeading) {
        EditButton()
    }
}
```

### Bottom Toolbar / Floating Action
```swift
.safeAreaInset(edge: .bottom) {
    Button {
        showCapture = true
    } label: {
        Label("New Memory", systemImage: "plus")
            .font(.headline)
            .frame(maxWidth: .infinity)
    }
    .buttonStyle(.borderedProminent)
    .controlSize(.large)
    .padding(.horizontal, 16)
    .padding(.bottom, 8)
    .background(.bar)
}
```

### Context Menu
```swift
.contextMenu {
    Button("Copy", systemImage: "doc.on.doc") { copy() }
    Button("Share", systemImage: "square.and.arrow.up") { share() }
    Divider()
    Button("Delete", systemImage: "trash", role: .destructive) { delete() }
} preview: {
    MemoryPreview(memory: memory) // Rich preview
        .frame(width: 300, height: 400)
}
```

---

## Search

```swift
.searchable(text: $searchText, prompt: "Search memories")
.searchSuggestions {
    if searchText.isEmpty {
        ForEach(recentSearches, id: \.self) { term in
            Text(term).searchCompletion(term)
        }
    }
}
.onChange(of: searchText) { _, newValue in
    filterResults(newValue)
}
```

- Always provide a descriptive `prompt`
- Use `.searchSuggestions` for recent/popular suggestions
- Debounce expensive search operations

---

## Pull to Refresh

```swift
List {
    // content
}
.refreshable {
    await viewModel.refresh()
}
```

- Use native `.refreshable` — never build a custom pull-to-refresh
- The async closure automatically shows/hides the spinner

---

## Confirmation & Deletion

### Swipe to Delete + Confirmation
```swift
.onDelete { indexSet in
    itemToDelete = items[indexSet.first!]
    showDeleteConfirmation = true
}
.confirmationDialog(
    "Delete Memory?",
    isPresented: $showDeleteConfirmation,
    titleVisibility: .visible
) {
    Button("Delete", role: .destructive) { performDelete() }
    Button("Cancel", role: .cancel) {}
} message: {
    Text("This will permanently delete this memory and its photos.")
}
```

- Always confirm destructive actions
- Use `.confirmationDialog` (action sheet) for destructive actions, `.alert` for critical system warnings
- Message should clearly explain consequences

---

## Scroll Behaviors

### Scroll Position Tracking (iOS 17+)
```swift
ScrollView {
    LazyVStack(spacing: 0) {
        ForEach(items) { item in
            ItemView(item: item)
                .id(item.id)
        }
    }
}
.scrollPosition(id: $scrolledID)
.scrollTargetLayout()
```

### Scroll to Top on Tab Re-Tap
Handle by resetting `scrolledID` when the current tab is tapped again.

---

## Section Headers

### Sticky Section Header
```swift
Section {
    // content
} header: {
    Text("January 2024")
        .font(.subheadline.weight(.semibold))
        .foregroundStyle(.secondary)
        .textCase(nil) // Prevent automatic uppercasing
}
```

- Use `.textCase(nil)` if you don't want the system's automatic uppercase
- Keep headers short — they're navigation landmarks, not descriptions
