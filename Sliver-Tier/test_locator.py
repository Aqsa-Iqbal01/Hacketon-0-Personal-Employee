"""
Test script to verify Locator functionality
"""

from playwright.sync_api import sync_playwright

def test_locator():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Test locator operations
        try:
            # Test basic locator
            locator = page.locator('body')
            print("Locator created successfully")

            # Test calling locator (should fail)
            try:
                result = locator()  # This should raise TypeError
                print("Locator called successfully (this should not happen)")
            except TypeError as e:
                print(f"Expected TypeError when calling locator: {e}")
                print("Locator test passed!")
            except Exception as e:
                print(f"Unexpected error: {e}")
        except Exception as e:
            print(f"Error creating locator: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    test_locator()