import XCTest
import WMFComponents

/// THROWAWAY (story-map screenshots only; lives in a scratch clone, never committed upstream).
final class StoryMapShotsUITests: XCTestCase {
    private func snap(_ base: UITestRobot, _ name: String) {
        Thread.sleep(forTimeInterval: 1.2)
        base.captureScreenshot(named: name)
    }

    private func home() -> HomeRobot {
        launchWikipediaAppRobot(onboardingState: .completed).home.assertVisible()
    }

    func testShotHome() throws {
        let h = home()
        snap(h.base, "home-explore")
    }

    func testShotPlaces() throws {
        let h = home().tapRootTab(.places)
        snap(h.base, "places")
    }

    func testShotSaved() throws {
        let h = home().tapRootTab(.saved)
        snap(h.base, "saved")
    }

    func testShotActivity() throws {
        let h = home().tapRootTab(.activity)
        snap(h.base, "activity")
    }

    func testShotSearchTab() throws {
        let h = home().tapRootTab(.search)
        snap(h.base, "search")
    }

    func testShotSearchResults() throws {
        let s = home().openSearch().focusSearchField().typeSearchTermOneCharacterAtATime("Dog")
            .assertSearchResultVisible(named: "Dog")
        snap(s.base, "search-results")
    }

    func testShotArticle() throws {
        let a = home().openSearch().focusSearchField().typeSearchTerm("Dog")
            .assertSearchResultVisible(named: "Dog").openResult(named: "Dog").assertVisible().assertTopControlsVisible()
        snap(a.base, "article")
        a.openTableOfContents()
        snap(a.base, "article-toc")
        a.dismissTableOfContentsByTappingOutside()
        a.openReadingThemeControls()
        snap(a.base, "article-theme")
        a.dismissReadingThemeControls()
        a.openOverflowMenu()
        snap(a.base, "article-overflow")
        a.dismissOverflowMenu()
        a.findInArticle(searchTerm: "wolf")
        snap(a.base, "article-find")
    }

    func testShotProfile() throws {
        let p = home().openProfile()
        snap(p.base, "profile")
        let app = p.base.app
        for label in ["Settings", "settings"] {
            let b = app.buttons[label].firstMatch
            let c = app.cells[label].firstMatch
            let t = app.staticTexts[label].firstMatch
            for e in [b, c, t] where e.waitForExistence(timeout: 2) && e.isHittable {
                e.tap()
                snap(p.base, "settings")
                return
            }
        }
        snap(p.base, "profile-nosettings")
    }

    private func openDog() -> ArticleRobot {
        home().openSearch().focusSearchField().typeSearchTerm("Dog")
            .assertSearchResultVisible(named: "Dog").openResult(named: "Dog").assertVisible().assertTopControlsVisible()
    }

    func testShotTabsOverview() throws {
        let a = home().openTabs()
        snap(a.base, "tabs-overview")
    }

    func testShotForYou() throws {
        let h = home()
        let b = h.base.app.buttons["For You"].firstMatch
        if b.waitForExistence(timeout: 5) { b.tap() }
        snap(h.base, "home-foryou")
    }

    func testShotLanguagePicker() throws {
        let a = openDog()
        a.base.tapButton(withIdentifier: AccessibilityIdentifiers.Article.languagesButton)
        snap(a.base, "article-languages")
    }

    func testShotImageGallery() throws {
        let a = openDog()
        let g = a.openLeadImageGallery()
        snap(g.base, "image-gallery")
    }

    func testShotSavedWithArticle() throws {
        let a = openDog()
        a.tapSaveAndAssertStateChanges()
        let h = a.tapHomeButtonToHome().tapRootTab(.saved)
        snap(h.base, "saved-article")
    }

    func testShotSettingsDeep() throws {
        let p = home().openProfile()
        let app = p.base.app
        let s = app.cells["Settings"].firstMatch
        let sb = s.exists ? s : app.buttons["Settings"].firstMatch
        XCTAssertTrue(sb.waitForExistence(timeout: 5))
        sb.tap()
        snap(p.base, "settings")
        for (label, shot) in [("My languages", "settings-languages"), ("App theme", "settings-theme"), ("Push notifications", "settings-notifications"), ("Article storage and syncing", "settings-storage")] {
            let c = app.cells.containing(.staticText, identifier: label).firstMatch
            let t = c.exists ? c : app.staticTexts[label].firstMatch
            if t.waitForExistence(timeout: 3) && t.isHittable {
                t.tap()
                snap(p.base, shot)
                let back = app.navigationBars.buttons.element(boundBy: 0)
                if back.exists { back.tap() }
            }
        }
    }

    func testShotLogin() throws {
        let p = home().openProfile()
        let app = p.base.app
        let b = app.buttons.matching(NSPredicate(format: "label CONTAINS[c] 'Log in'")).firstMatch
        let c = app.cells.matching(NSPredicate(format: "label CONTAINS[c] 'Log in'")).firstMatch
        let t = b.exists ? b : c
        XCTAssertTrue(t.waitForExistence(timeout: 5))
        t.tap()
        snap(p.base, "login")
    }

    func testShotDonate() throws {
        let p = home().openProfile()
        let app = p.base.app
        let b = app.buttons.matching(NSPredicate(format: "label CONTAINS[c] 'Donate'")).firstMatch
        let c = app.cells.matching(NSPredicate(format: "label CONTAINS[c] 'Donate'")).firstMatch
        let t = b.exists ? b : c
        XCTAssertTrue(t.waitForExistence(timeout: 5))
        t.tap()
        sleep(3)
        snap(p.base, "donate")
    }
}
