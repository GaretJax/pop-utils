$folder = "popc"

exec { "untar":
	command => "tar -xzf ${folder}.tar.gz",
	cwd => "/var/uploads/packages",
	path => ['/usr/bin', '/bin'],
	unless => 'which SXXpopc',
}

exec { "configure":
	command => "./configure",
	cwd => "/var/uploads/packages/${folder}",
	path => ['/usr/bin', '/bin'],
	unless => 'which SXXpopc',
	require => Exec["untar"],
}

exec { "build":
	command => "make",
	cwd => "/var/uploads/packages/${folder}",
	path => ['/usr/bin', '/bin'],
	unless => 'which SXXpopc',
	require => Exec["configure"],
}

exec { "install":
	command => "yes | make install",
	cwd => "/var/uploads/packages/${folder}",
	path => ['/usr/bin', '/bin'],
	unless => 'which SXXpopc',
	require => Exec["build"],
}

file { "/etc/profile.d/popc.sh":
	ensure => present,
	content => 'export POPC_LOCATION=/usr/local/popc
export PATH=$PATH:$POPC_LOCATION/bin:$POPC_LOCATION/sbin
',
}

exec { "update-root-path":
	command => "cat /etc/profile.d/popc.sh >>/root/.bashrc",
	path => ['/usr/bin', '/bin'],
	unless => 'grep "$(cat /etc/profile.d/popc.sh)" /root/.bashrc',
	require => [File["/etc/profile.d/popc.sh"], Exec["install"]],
}

file { "/etc/init.d/popc-jobmgr":
	ensure => file,
	source => "/var/uploads/scripts/service.sh",
	mode => 755,
	owner => root,
	group => root,
	replace => true,
	require => Exec["update-root-path"],
}

exec { "service":
	command => "update-rc.d -f popc-jobmgr start 99 2 3 4 5 . stop 20 0 1 6 .",
	path => ['/usr/sbin'],
	require => File["/etc/init.d/popc-jobmgr"],
}

service { "popc-jobmgr":
	require => File["/etc/init.d/popc-jobmgr"],
	ensure => running,
	hasrestart => true,
	hasstatus => true,
}