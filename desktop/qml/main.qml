import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import "components"
import "views"

ApplicationWindow {
    id: window
    visible: true
    width: 1140
    height: 750
    minimumWidth: 980
    minimumHeight: 640
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
                        case 4: return "Storage location, cache backup and local statistics";
                        default: return "";
                    }
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
                }

                ResolverView {
                    id: resolverView
                }

                QueueView {
                    id: queueView
                }

                LibraryView {
                    id: libraryView
                    onOpenGallery: function(images, title) {
                        lightbox.open(images, title, 0)
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
                onOpenQueueRequested: window.activeTab = 2
            }
        }
    }

    // Global Photo Lightbox Modal
    LightboxModal {
        id: lightbox
    }

    // Global Category Picker Modal
    BulkPickerModal {
        id: bulkPicker
        limitValue: categoriesView.limitValue
        wantModels: categoriesView.wantModels
        wantImages: categoriesView.wantImages
    }

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

    // Global Toast Notification
    ToastNotification {
        id: toastWidget
    }
}
