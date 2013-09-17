on run argv
	tell application "Alfred 2"
		activate

		try
			set choices to {choices}
			choose from list choices with prompt "{prompt}" with title ¬
				"{title}" default items "{default}"
			set answer to (button returned of result) & "|" & ¬
				(text returned of result)
		on error number -128
			set answer to "Cancel|"
		end
	end tell
end run
