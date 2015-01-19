on run argv
	tell application "Alfred 2"
		activate

		set choices to {choices}
		choose from list choices with prompt "{prompt}" with title ¬
			"{title}" default items "{default}" {multiple} multiple selections allowed

		if result is false
			set answer to "Cancel|"
		else
			set answer to "Ok|" & result
		end
	end tell
end run
