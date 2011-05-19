exec { "disablechecking":
	command => "echo '    StrictHostKeyChecking no' >>/etc/ssh/ssh_config",
	path => ['/usr/bin', '/bin'],
	unless => "grep 'StrictHostKeyChecking no' /etc/ssh/ssh_config",
}


exec { "disablehostsfile":
	command => "echo '    UserKnownHostsFile /dev/null' >>/etc/ssh/ssh_config",
	path => ['/usr/bin', '/bin'],
	unless => "grep 'UserKnownHostsFile /dev/null' /etc/ssh/ssh_config",
}
