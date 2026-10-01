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

    property int activeTab: 1

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
                        case 0: return "Explore 3D Models";
                        case 1: return "Categories & Feeds";
                        case 2: return "Direct URL Resolver";
                        case 3: return "Downloads Library";
                        case 4: return "Settings & Integration";
                        default: return "CGTips 3D";
                    }
                }
                subtitle: {
                    switch (window.activeTab) {
                        case 0: return "Search and discover free SketchUp 3D models from CGTips";
                        case 1: return "Browse category hierarchy and live RSS article feeds";
                        case 2: return "Bypass download lockers and fetch 3D model archives";
                        case 3: return "Manage and download locally saved 3D models";
                        case 4: return "Configure backend server address, API key, and view statistics";
                        default: return "";
                    }
                }
                onSearchRequested: function(query) {
                    window.activeTab = 0
                    Bridge.performSearch(query, 1)
                }
            }

            // Views Stack
            StackLayout {
                id: viewsStack
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: window.activeTab

                ExploreView {
                    id: exploreView
                    onOpenGallery: function(images, title) {
                        lightbox.open(images, title, 0)
                    }
                    onResolveRequested: function(link) {
                        resolverView.setUrl(link)
                        window.activeTab = 2
                    }
                }

                CategoriesView {
                    id: categoriesView
                    onOpenCategoryModalRequested: function() {
                        categoryModal.open()
                    }
                    onResolveRequested: function(link) {
                        resolverView.setUrl(link)
                        window.activeTab = 2
                    }
                }

                ResolverView {
                    id: resolverView
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
        }
    }

    // Global Photo Lightbox Modal
    LightboxModal {
        id: lightbox
    }

    // Global Category Picker Modal
    CategoryModal {
        id: categoryModal
        selectedCategory: categoriesView.selectedCategoryName
        selectedSubcategory: categoriesView.selectedSubcategoryName
        selectedFeedUrl: categoriesView.selectedFeedUrl
        onSubcategorySelected: function(catTitle, subTitle, feedUrl) {
            categoriesView.selectSubcategory(catTitle, subTitle, feedUrl)
            window.activeTab = 1
        }
    }

    // Global Toast Notification
    ToastNotification {
        id: toastWidget
    }
}
