use strict;
use warnings;
use POSIX qw(floor);

package PyRandom;
sub _u32 { my ($x)=@_; return $x % 4294967296; }
sub _rshift { my ($x,$n)=@_; return int(_u32($x) / (2 ** $n)); }
sub _lshift { my ($x,$n)=@_; return _u32(_u32($x) * (2 ** $n)); }
sub new {
  my ($class, $seed) = @_;
  my $self = bless { mt => [(0)x624], index => 624 }, $class;
  $self->seed($seed);
  return $self;
}
sub seed {
  my ($self,$seed)=@_;
  my @key;
  my $n = $seed;
  if ($n == 0) { @key = (0); }
  else {
    while ($n > 0) {
      push @key, $n % 4294967296;
      $n = int($n / 4294967296);
    }
  }
  $self->_init_by_array(\@key);
}
sub _init_genrand {
  my ($self,$s)=@_;
  $self->{mt}[0] = _u32($s);
  for my $i (1..623) {
    my $prev = $self->{mt}[$i-1];
    $self->{mt}[$i] = _u32(1812433253 * ($prev ^ _rshift($prev,30)) + $i);
  }
  $self->{index}=624;
}
sub _init_by_array {
  my ($self,$key)=@_;
  my $key_length = scalar(@$key);
  $self->_init_genrand(19650218);
  my ($i,$j)=(1,0);
  my $k = 624 > $key_length ? 624 : $key_length;
  while ($k--) {
    my $prev = $self->{mt}[$i-1];
    $self->{mt}[$i] = _u32(($self->{mt}[$i] ^ _u32(($prev ^ _rshift($prev,30)) * 1664525)) + $key->[$j] + $j);
    $i++; $j++;
    if ($i >= 624) { $self->{mt}[0] = $self->{mt}[623]; $i = 1; }
    if ($j >= $key_length) { $j = 0; }
  }
  $k = 623;
  while ($k--) {
    my $prev = $self->{mt}[$i-1];
    $self->{mt}[$i] = _u32(($self->{mt}[$i] ^ _u32(($prev ^ _rshift($prev,30)) * 1566083941)) - $i);
    $i++;
    if ($i >= 624) { $self->{mt}[0] = $self->{mt}[623]; $i = 1; }
  }
  $self->{mt}[0] = 2147483648;
}
sub _twist {
  my ($self)=@_;
  for my $i (0..623) {
    my $y = ($self->{mt}[$i] & 2147483648) + ($self->{mt}[($i+1)%624] & 2147483647);
    my $v = $self->{mt}[($i+397)%624] ^ _rshift($y,1);
    $v ^= 2567483615 if ($y % 2) != 0;
    $self->{mt}[$i] = _u32($v);
  }
  $self->{index}=0;
}
sub _genrand_int32 {
  my ($self)=@_;
  $self->_twist() if $self->{index} >= 624;
  my $y = $self->{mt}[ $self->{index}++ ];
  $y ^= _rshift($y,11);
  $y ^= (_lshift($y,7) & 2636928640);
  $y ^= (_lshift($y,15) & 4022730752);
  $y ^= _rshift($y,18);
  return _u32($y);
}
sub getrandbits {
  my ($self,$k)=@_;
  return 0 if $k == 0;
  if ($k <= 32) {
    my $r = $self->_genrand_int32();
    return _rshift($r, 32-$k);
  }
  my $words = int(($k - 1)/32) + 1;
  my $acc = 0;
  my $mul = 1;
  for my $i (0..$words-1) {
    my $r = $self->_genrand_int32();
    if ($i == $words - 1) {
      my $rem = $k - 32*$i;
      $r = _rshift($r, 32-$rem) if $rem < 32;
    }
    $acc += $r * $mul;
    $mul *= 4294967296;
  }
  return $acc;
}
sub _randbelow {
  my ($self,$n)=@_;
  my $k = 0; my $m = $n - 1; while ($m > 0) { $k++; $m = int($m/2); }
  while (1) { my $r = $self->getrandbits($k); return $r if $r < $n; }
}
sub randint { my ($self,$a,$b)=@_; return $a + $self->_randbelow($b-$a+1); }
sub choice_idx { my ($self,$n)=@_; return $self->_randbelow($n); }
sub random {
  my ($self)=@_;
  my $a = _rshift($self->_genrand_int32(),5);
  my $b = _rshift($self->_genrand_int32(),6);
  return ($a * 67108864.0 + $b) / 9007199254740992.0;
}
sub sample_indices {
  my ($self,$n,$k)=@_;
  my @result;
  my $setsize = 21;
  if ($k > 5) {
    my $pow4 = 1;
    while ($pow4 < $k * 3) { $pow4 *= 4; }
    $setsize += $pow4;
  }
  if ($n <= $setsize) {
    my @pool = (0..$n-1);
    for my $i (0..$k-1) {
      my $j = $self->_randbelow($n-$i);
      $result[$i] = $pool[$j];
      $pool[$j] = $pool[$n-$i-1];
    }
  } else {
    my %selected;
    for my $i (0..$k-1) {
      my $j = $self->_randbelow($n);
      while (exists $selected{$j}) { $j = $self->_randbelow($n); }
      $selected{$j}=1;
      $result[$i]=$j;
    }
  }
  return @result;
}

package main;
sub count_words {
  my ($path)=@_;
  open my $fh,'<',$path or die $!;
  my ($in,$count)=(0,0);
  while (my $line=<$fh>) {
    if ($line =~ /word_list\s*=\s*\(/) { $in=1; next; }
    last if $in && $line =~ /^\s*\)/;
    if ($in) { while ($line =~ /"([^"]*)"/g) { $count++; } }
  }
  close $fh;
  return $count;
}
my $N = count_words('/testbed/faker/providers/lorem/en_US/__init__.py');
my @letters = split //, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
my $r = PyRandom->new(424242);
sub pystr20 { my ($r)=@_; my $s=''; for (1..20) { $s .= $letters[floor($r->random()*52.0)]; } return $s; }
sub pyint0 { my ($r)=@_; return $r->randint(0,9999); }
sub pyfloat0 {
  my ($r)=@_;
  my $right = $r->randint(1,14);
  my $left_digits = 15 - $right; $left_digits = 1 if $left_digits < 1;
  my $sign = $r->choice_idx(2) == 0 ? '+' : '-';
  my $left = $r->randint(0, (10**$left_digits)-1);
  my $frac = $r->randint(0, (10**$right)-1);
  my $num = 0 + ($sign . $left . '.' . $frac);
  if ($right) {
    my $max = (10**$left_digits) - (10**(-$right));
    my $min = -(10**$left_digits + (10**(-$right)));
    $num = $max if $num > $max;
    $num = $min if $num < $min;
  }
  return $num;
}
sub rt {
  my ($r,$types)=@_;
  my @t = @$types;
  my $sel = $t[$r->choice_idx(scalar(@t))];
  return pystr20($r) if $sel eq 'str';
  return pyint0($r) if $sel eq 'int';
  return pyfloat0($r);
}
my $types_pystruct = ['str','int','float'];
my $types_pydict = ['int','str','float'];
for my $iter (1..3) {
  $r->choice_idx($N);
  rt($r,$types_pystruct);
  rt($r,$types_pystruct);
  $r->choice_idx($N);
  for (1..8) { rt($r,$types_pystruct); }
}
my $pct = $r->randint(60,140);
my $nb = int(4 * $pct / 100); $nb = 1 if $nb < 1;
my @sample = $r->sample_indices($N,$nb);
my @vals; for (1..$nb) { push @vals, rt($r,$types_pydict); }
print "N=$N pct=$pct nb=$nb\n";
print "$_\n" for @vals;
