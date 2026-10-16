import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import "components"
import "views"

ApplicationWindow {
    id: window
    visible: true
    width: 1560
    height: 960
    minimumWidth: 1080
    minimumHeight: 680
    title: "CGTips 3D • Desktop Platform"
    color: Theme.background

    property int activeTab: 0

    // Font Awesome Loaders
    FontLoader {
        id: faSolidLoader
        source: "../assets/fonts/fa-solid-900.ttf"
    }
    FontLoader {
        id: faRegularLoader
        source: "../assets/fonts/fa-regular-400.ttf"
    }

    // Connect toast signal from Python bridge
    Connections {
        target: Bridge
        function onToast(type, msg) {
            toastWidget.showToast(type, msg)
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar Navigation
        SidebarNav {
            id: sidebar
            Layout.preferredWidth: 220
            Layout.minimumWidth: 220
            Layout.maximumWidth: 220
            Layout.fillWidth: false
            Layout.fillHeight: true
            activeTab: window.activeTab
            onTabSelected: function(index) {
                window.activeTab = index
            }
        }

        // Main Content Area
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // Top Header Bar
            HeaderBar {
                id: header
                Layout.preferredHeight: 60
                Layout.minimumHeight: 60
                Layout.fillWidth: true
                Layout.fillHeight: false
                title: {
                    switch (window.activeTab) {
                        case 0: return "Categories & Feeds";
                        case 1: return "Direct URL Resolver";
                        case 2: return "Download Queue";
                        case 3: return "Downloads Library";
                        case 4: return "Settings & Integration";
                        default: return "CGTips 3D";
                    }
                }
                subtitle: {
                    switch (window.activeTab) {
                        case 0: return "Browse category hierarchy and live RSS article feeds";
                        case 1: return "Bypass download lockers and fetch 3D model archives";
                        case 2: return "Pause, resume and retry queued model downloads";
                        case 3: return "Manage and download locally saved 3D models";
                        case 4: return "Configure backend server address, API key, and view statistics";
                        default: return "";
                    }
                }
                onSearchRequested: function(query) {
                    window.activeTab = 3
                    libraryView.setSearch(query)
                }
                onOpenQueueRequested: function() {
                    window.activeTab = 2
                }
            }

            // Views Stack
            StackLayout {
                id: viewsStack
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: window.activeTab

                CategoriesView {
                    id: categoriesView
                    onOpenCategoryModalRequested: function() {
                        categoryModal.open()
                    }
                    onOpenBulkPickerRequested: function() {
                        bulkPicker.open()
                    }
                    onResolveRequested: function(link) {
                        resolverView.setUrl(link)
                        window.activeTab = 1
                    }
                    onOpenBatchDownloadRequested: function(scope, cat, sub, articleFolder, articleTitle) {
                        batchDownloadModal.open(scope, cat, sub, articleFolder, articleTitle)
                    }
                    onOpenCopyRequested: function(scope, cat, sub, articleFolder, articleTitle) {
                        copyModal.open(scope, cat, sub, articleFolder, articleTitle)
                    }
                    onOpenUploadRequested: function(scope, cat, sub, articleFolder, articleTitle) {
                        uploadModal.open(scope, cat, sub, articleFolder, articleTitle)
                    }
                }

                ResolverView {
                    id: resolverView
                }

                QueueView {
                    id: queueView
                    onOpenMissingModelsRequested: function() {
                        batchDownloadModal.open("all", "", "", "", "")
                    }
                }

                LibraryView {
                    id: libraryView
                    onOpenGallery: function(images, title) {
                        lightbox.open(images, title, 0)
                    }
                    onOpenBatchDownloadRequested: function(scope, cat, sub, articleFolder, articleTitle) {
                        batchDownloadModal.open(scope, cat, sub, articleFolder, articleTitle)
                    }
                    onOpenCopyRequested: function(scope, cat, sub, articleFolder, articleTitle) {
                        copyModal.open(scope, cat, sub, articleFolder, articleTitle)
                    }
                    onOpenUploadRequested: function(scope, cat, sub, articleFolder, articleTitle) {
                        uploadModal.open(scope, cat, sub, articleFolder, articleTitle)
                    }
                    onOpenClearConfirmRequested: function() {
                        clearConfirmModal.open()
                    }
                }

                SettingsView {
                    id: settingsView
                }
            }

            // Bulk download progress (shown on every tab while a job exists)
            BulkProgressBar {
                Layout.fillWidth: true
                Layout.preferredHeight: implicitHeight
                onOpenQueueRequested: function() {
                    window.activeTab = 2
                }
            }
        }
    }

    // Global Photo Lightbox Modal
    LightboxModal {
        id: lightbox
    }

    // Global Category Picker Modal (Bulk Download)
    BulkPickerModal {
        id: bulkPicker
        limitValue: categoriesView.limitValue
        wantModels: categoriesView.wantModels
        wantImages: categoriesView.wantImages
    }

    // Global Category Tree Modal (Single Category Selection)
    CategoryModal {
        id: categoryModal
        selectedCategory: categoriesView.selectedCategoryName
        selectedSubcategory: categoriesView.selectedSubcategoryName
        selectedFeedUrl: categoriesView.selectedFeedUrl
        onSubcategorySelected: function(catTitle, subTitle, feedUrl) {
            categoriesView.selectSubcategory(catTitle, subTitle, feedUrl)
            window.activeTab = 0
        }
    }

    // Global Batch Download Modal
    BatchDownloadModal {
        id: batchDownloadModal
    }

    // Global Multi-Destination Copy Modal
    CopyModal {
        id: copyModal
    }

    // Global Loft Design Upload Modal
    UploadModal {
        id: uploadModal
    }

    // Global Clear Download List Modal
    ClearConfirmModal {
        id: clearConfirmModal
    }

    // Global Toast Notification
    ToastNotification {
        id: toastWidget
    }
}
