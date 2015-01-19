on run argv
	tell application "Alfred 2"
		activate
		set alfredPath to (path to application "Alfred 2")
		set alfredIcon to path to resource "appicon.icns" in bundle (alfredPath as alias)
		
		try
			display dialog "{p}" with title "{t}" buttons {{"Yes", "No"}} default button "{d}" with icon alfredIcon
			set answer to (button returned of result)
		on error number -128
			set answer to "No"
		end try
	end tell
end run
